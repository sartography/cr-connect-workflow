import hashlib
import json
import os
import re
from lxml.html import builder as htm

import pandas as pd
import requests
from lxml import etree
from pandas._libs.missing import NA
from crc import app, session
from crc.api.common import ApiError
from crc.api.workflow import get_workflow_specification
from crc.models.file import FileModel, FileDataModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowSpecCategoryModel, \
    WorkflowSpecCategoryModelSchema, WorkflowLibraryModel
from crc.services.file_service import FileService


def parse_key(key):
    return key.split("__")[1:]

def spantext(text,color):
    node = htm.SPAN(text)
    node.set('style','color: ' +color+";")
    return node


spec_lookup_table = {
    # location new  keep_new_local status
    'local,True,True':  'keep',
    'local,True,False': 'delete',
    'local,False,.+':  'revert',
    'remote,True,.+':   'copy',
    'remote,False,.+':  'update',
}

file_lookup_table = {
    'local,True,keep': 'keep',
    'local,True,.+': 'delete',
    'local,False,.+': 'revert',
    'remote,True,.+': 'copy',
    'remote,False,.+': 'update',
}


def join_uuids(uuids):
    """Joins a pandas Series of uuids and combines them in one hash"""
    combined_uuids = ''.join([str(uuid) for uuid in uuids.sort_values()]) # ensure that values are always
                                                                          # in the same order
    return hashlib.md5(combined_uuids.encode('utf8')).hexdigest() # make a hash of the hashes


class WorkflowSyncService(object):

    @staticmethod
    def get_remote_file_by_hash(remote,md5_hash):
        url = remote+'/v1.0/file/'+md5_hash+'/hash_data'
        return WorkflowSyncService.__make_request(url,return_contents=True)

    @staticmethod
    def get_remote_workflow_spec_files(remote,workflow_spec_id):
        url = remote+'/v1.0/workflow_sync/'+workflow_spec_id+'/files'
        return WorkflowSyncService.__make_request(url)

    @staticmethod
    def get_remote_workflow_spec(remote, workflow_spec_id):
        """
        this just gets the details of a workflow spec from the
        remote side.
        """
        url = remote+'/v1.0/workflow_sync/'+workflow_spec_id+'/spec'
        return WorkflowSyncService.__make_request(url)

    @staticmethod
    def publish_remote_repository(remote,message):
        url = remote + '/v1.0/file/needs_publish'
        result = WorkflowSyncService.__make_request(url)
        if result.json == True:
            url = remote + '/v1.0/file/publish'
            return WorkflowSyncService.__make_request(url,body={'message':message},post=True)
        return result

    @staticmethod
    def get_all_remote_workflows(remote):
        url = remote + '/v1.0/workflow_sync/all'
        return WorkflowSyncService.__make_request(url)

    @staticmethod
    def __make_request(url,body={},post=False,return_contents=False):
        if post:
            try:
                response = requests.post(url,body, headers={'X-CR-API-KEY': app.config['API_TOKEN']})
            except:
                raise ApiError("workflow_sync_error", url)
        else:
            try:
                response = requests.get(url,headers={'X-CR-API-KEY':app.config['API_TOKEN']})
            except:
                raise ApiError("workflow_sync_error",url)
        if response.ok and response.text:
            if return_contents:
                return response.content
            else:
                return json.loads(response.text)
        else:
            raise ApiError("workflow_sync_error",
                           "Received an invalid response from the remote CR-Connect API (status %s): %s when calling "
                           "url '%s'." %
                           (response.status_code, response.text, url))

    @staticmethod
    def get_sync_sources():
        """Environment variables for sync sources should be in the following format
        CR_SYNC_SOURCE__0__url=https://my.target.com
        CR_SYNC_SOURCE__0__name="source name"
        CR_SYNC_SOURCE__1__url=https://my.target2.com
        CR_SYNC_SOURCE__1__name="source2 name"

        This function will build a structure based on these environment variables that will look like:
        [{'url':'https://my.target.com','name':'source name'},
         {'url':'https://my.target2.com','name':'source2 name'}]
        """
        sources = {}
        mykeys=[key for key in os.environ.keys() if key.startswith('CR_SYNC_SOURCE')]
        for key in mykeys:
            loc = parse_key(key)
            mydict = sources.get(loc[0],dict())
            mydict[loc[1]] = os.environ.get(key)
            sources[loc[0]] = mydict
        return [sources[key] for key in sources.keys()]


    @staticmethod
    def sync_all_changed_workflows(remote,message="syncing between systems",keep_new_local=False):
        """
        Does what it says, gets a list of all workflows that are different between
        two systems and pulls all of the workflows and files that are different on the
        remote system. The idea is that we can make the local system 'look' like the remote
        system for deployment or testing.
        I originally thought that we would do a pre/post commit in this function,
        but . . .  I thought it would be good to show a status on the front end, so you mush
        do this independently
        """
        tree = WorkflowSyncService.get_master_list(remote,keep_new_local)
        info = {}
        # first, delete local files that are not in the remote or that will be superseded by remote
        for category in tree.keys():
            for workflow in tree[category]:
                for file in workflow['files']:
                    if file['status'] in ['delete','revert']:
                        print('delete file',file)

                        file = session.query(FileModel).filter(FileModel.name==file['filename']).first()
                        FileService.delete_file(file.id)
                        #file.archived = True
                        #session.commit()
                if workflow['status'] in ['delete']:
                    session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==workflow[
                        'workflow_spec_id']).delete()

                    session.commit()
                    print('delete workflow',workflow)
                else:
                    files = WorkflowSyncService.sync_changed_files(remote,workflow['workflow_spec_id'])
                    workflow['changed_files'] = files
                    info[workflow['workflow_spec_id']] = {'name': workflow['name'],
                                                    'files': workflow['changed_files']}
        ref_files = WorkflowSyncService.sync_changed_files(remote,'REFERENCE_FILES')
        info['reference_files'] = ref_files
        return info


    def get_master_list(remote,keep_new_local=False):
        # first let's just build a local tree
        changed = WorkflowSyncService.get_changed_workflows(remote,keep_new_local=keep_new_local)
        lcl_specs = WorkflowSyncService.get_all_spec_state()
        categories = {}
        lcl_spec_ids = [x['workflow_spec_id'] for x in lcl_specs]
        for wf in changed:
            if wf['workflow_spec_id'] in lcl_spec_ids:
                fullspec = get_workflow_specification(wf['workflow_spec_id'])
            else:
                fullspec = WorkflowSyncService.get_remote_workflow_spec(remote,wf['workflow_spec_id'])
            category = fullspec['category']
            if category is None:
                category = {'display_name': 'Top Level Workflow'}
            spec = {}
            spec.update(wf)
            spec['status'] = wf['location']
            spec['new'] = wf['new']
            spec['status'] = WorkflowSyncService.lookup_status([wf['location'], wf['new'], keep_new_local], spec_lookup_table)
            spec['files'] = WorkflowSyncService.get_changed_files(remote, spec['workflow_spec_id'])
            for file in spec['files']:
                file['status'] = WorkflowSyncService.lookup_status([file['location'], file['new'], spec['status']], file_lookup_table)
            catlist = categories.get(category['display_name'], [])
            catlist.append(spec)
            categories[category['display_name']] = catlist
        return categories

    @staticmethod
    def get_changed_workflows(remote,as_df=False,keep_new_local=False):
        """
        gets a remote endpoint - gets the workflows and then
        determines what workflows are different from the remote endpoint
        """

        remote_workflows_list = WorkflowSyncService.get_all_remote_workflows(remote)
        remote_workflows = pd.DataFrame(remote_workflows_list)

        # get the local thumbprints & make sure that 'workflow_spec_id' is a column, not an index
        local = WorkflowSyncService.get_all_spec_state_dataframe().reset_index()

        if local.empty:
            # return the list as a dict, let swagger convert it to json
            remote_workflows['new'] = True
            if as_df:
                return remote_workflows
            else:
                return remote_workflows.reset_index().to_dict(orient='records')

        # merge these on workflow spec id and hash - this will
        # make two different date columns date_x and date_y
        different = remote_workflows.merge(local,
                                  right_on=['workflow_spec_id','md5_hash'],
                                  left_on=['workflow_spec_id','md5_hash'],
                                  how = 'outer' ,
                                  indicator=True).loc[lambda x : x['_merge']!='both']

        # If there are no differences, then we can just return.
        if not different.empty:

            # each line has a tag on it - if was in the left or the right,
            # label it so we know if that was on the remote or local machine
            different.loc[different['_merge']=='left_only','location'] = 'remote'
            different.loc[different['_merge']=='right_only','location'] = 'local'

            # this takes the different date_created_x and date-created_y columns and
            # combines them back into one date_created column
            index = different['date_created_x'].isnull()
            different.loc[index, 'date_created_x'] = different[index]['date_created_y']
            different.loc[index, 'name_x'] = different[index]['name_y']

            different = different[['workflow_spec_id','date_created_x','location','name_x']].copy()
            different.columns=['workflow_spec_id','date_created','location','name']

            # our different list will have multiple entries for a workflow if there is a version on either side
            # we want to grab the most recent one, so we sort and grab the most recent one for each workflow
            changedfiles = different.sort_values('date_created',ascending=False).groupby('workflow_spec_id').first()

            # get an exclusive or list of workflow ids - that is we want lists of files that are
            # on one machine or the other, but not both
            remote_spec_ids = remote_workflows[['workflow_spec_id']]
            local_spec_ids = local[['workflow_spec_id']]
            left = remote_spec_ids[~remote_spec_ids['workflow_spec_id'].isin(local_spec_ids['workflow_spec_id'])]
            right = local_spec_ids[~local_spec_ids['workflow_spec_id'].isin(remote_spec_ids['workflow_spec_id'])]

            # flag files as new that are only on the remote box and remove the files that are only on the local box
            changedfiles['new'] = False
            changedfiles.loc[changedfiles.index.isin(left['workflow_spec_id']), 'new'] = True
            changedfiles.loc[changedfiles.index.isin(right['workflow_spec_id']), 'new'] = True
            output = changedfiles
            if keep_new_local:
                output = changedfiles[~changedfiles.index.isin(right['workflow_spec_id'])]

        else:
            output = different

        # return the list as a dict, let swagger convert it to json
        if as_df:
            return output
        else:
            return output.reset_index().to_dict(orient='records')

    @staticmethod
    def file_get(workflow_spec_id,filename):
        """
        Helper function to take care of the special case where we
        are looking for files that are marked is_reference
        """
        if workflow_spec_id == 'REFERENCE_FILES':
            currentfile = session.query(FileModel).filter(FileModel.is_reference == True,
                                                          FileModel.name == filename).first()
        else:
            currentfile = session.query(FileModel).filter(FileModel.workflow_spec_id==workflow_spec_id,
                                                FileModel.name == filename).first()
        return currentfile

    @staticmethod
    def create_or_update_local_spec(remote,workflow_spec_id):
        specdict = WorkflowSyncService.get_remote_workflow_spec(remote, workflow_spec_id)
        # if we are updating from a master spec, then we want to make sure it is the only
        # master spec in our local system, turn all other master_specs off
        if specdict['is_master_spec']:
            master_specs = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.is_master_spec == True).all()
            for master_spec in master_specs:
                master_spec.is_master_spec = False
                session.add(master_spec)

        # Update local_spec, or create a new one if one does not exist.
        local_spec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == workflow_spec_id).first()
        local_spec = WorkflowSpecModelSchema().load(specdict, session=session, instance=local_spec)

        # Set the category
        if specdict['category'] is not None:
            local_category = session.query(WorkflowSpecCategoryModel).\
                filter(WorkflowSpecCategoryModel.name == specdict['category']['name']).first()
            if local_category is None:
                local_category = WorkflowSpecCategoryModelSchema().load(specdict['category'], session=session,
                                                                    instance=local_category)
                session.add(local_category)
            local_spec.category = local_category

        # Set the libraries
        session.query(WorkflowLibraryModel).filter(WorkflowLibraryModel.workflow_spec_id == local_spec.id).delete()
        for library in specdict['libraries']:
            # Assure refernced libraries are local, and link them.
            WorkflowSyncService.create_or_update_local_spec(remote, library['id'])
            local_lib = WorkflowLibraryModel(workflow_spec_id=local_spec.id,
                                             library_spec_id=library['id'])
            session.add(local_lib)
        session.add(local_spec)

    @staticmethod
    def update_or_create_current_file(remote,workflow_spec_id,updatefile):
        currentfile = WorkflowSyncService.file_get(workflow_spec_id, updatefile['filename'])
        if not currentfile:
            currentfile = FileModel()
            currentfile.name = updatefile['filename']
            if workflow_spec_id == 'REFERENCE_FILES':
                currentfile.workflow_spec_id = None
                currentfile.is_reference = True
            else:
                currentfile.workflow_spec_id = workflow_spec_id

        currentfile.date_created = updatefile['date_created']
        currentfile.type = updatefile['type']
        currentfile.primary = updatefile['primary']
        currentfile.content_type = updatefile['content_type']
        currentfile.primary_process_id = updatefile['primary_process_id']
        session.add(currentfile)
        try:
            content = WorkflowSyncService.get_remote_file_by_hash(remote, updatefile['md5_hash'])
            FileService.update_file(currentfile, content, updatefile['type'])
        except ApiError:
            # Remote files doesn't exist, don't update it.
            print("Remote file " + currentfile.name + " does not exist, so not syncing.")

    @staticmethod
    def sync_changed_files(remote, workflow_spec_id):
        """
        This grabs a list of all files for a workflow_spec that are different between systems,
        and gets the remote copy of any file that has changed

        We also have a special case for "REFERENCE_FILES" where there is not workflow_spec_id,
        but all of the files are marked in the database as is_reference - and they need to be
        handled slightly differently.
        """
        # make sure that spec is local before syncing files
        if workflow_spec_id != 'REFERENCE_FILES':
            WorkflowSyncService.create_or_update_local_spec(remote,workflow_spec_id)


        changedfiles = WorkflowSyncService.get_changed_files(remote,workflow_spec_id,as_df=True)
        if len(changedfiles)==0:
            return []
        updatefiles = changedfiles[~((changedfiles['new']==True) & (changedfiles['location']=='local'))]
        updatefiles = updatefiles.reset_index().to_dict(orient='records')

        deletefiles = changedfiles[((changedfiles['new']==True) & (changedfiles['location']=='local'))]
        deletefiles = deletefiles.reset_index().to_dict(orient='records')

        for delfile in deletefiles:
            currentfile = WorkflowSyncService.file_get(workflow_spec_id,delfile['filename'])

            # it is more appropriate to archive the file than delete
            # due to the fact that we might have workflows that are using the
            # file data
            currentfile.archived = True
            session.add(currentfile)

        for updatefile in updatefiles:
            WorkflowSyncService.update_or_create_current_file(remote,workflow_spec_id,updatefile)
        session.commit()
        return [x['filename'] for x in updatefiles]

    @staticmethod
    def get_changed_files(remote,workflow_spec_id,as_df=False):
        """
        gets a remote endpoint - gets the files for a workflow_spec on both
        local and remote and determines what files have been change and returns a list of those
        files
        """
        remote_file_list = WorkflowSyncService.get_remote_workflow_spec_files(remote,workflow_spec_id)
        remote_files = pd.DataFrame(remote_file_list)
        if remote_files.empty:
            remote_files = pd.DataFrame(columns=['filename','md5_hash','date_created','type','primary','content_type','primary_process_id'])
        # get the local thumbprints & make sure that 'workflow_spec_id' is a column, not an index
        local = WorkflowSyncService.get_workflow_spec_files_dataframe(workflow_spec_id).reset_index()
        local['md5_hash'] = local['md5_hash'].astype('str')
        remote_files['md5_hash'] = remote_files['md5_hash'].astype('str')
        if len(local) == 0:
            remote_files['new'] = True
            remote_files['location'] = 'remote'
            if as_df:
                return remote_files
            else:
                return remote_files.reset_index().to_dict(orient='records')

        different = remote_files.merge(local,
                                 right_on=['filename','md5_hash'],
                                 left_on=['filename','md5_hash'],
                                 how = 'outer' ,
                                 indicator=True).loc[lambda x : x['_merge']!='both']
        if len(different) == 0:
            if as_df:
                return different
            else:
                return []
        # each line has a tag on it - if was in the left or the right,
        # label it so we know if that was on the remote or local machine
        different.loc[different['_merge']=='left_only','location'] = 'remote'
        different.loc[different['_merge']=='right_only','location'] = 'local'

        # this takes the different date_created_x and date-created_y columns and
        # combines them back into one date_created column
        dualfields = ['date_created','type','primary','content_type','primary_process_id']
        for merge in dualfields:
            index = different[merge+'_x'].isnull()
            different.loc[index,merge+'_x'] = different[index][merge+'_y']

        fieldlist = [fld+'_x' for fld in dualfields]
        different = different[ fieldlist + ['md5_hash','filename','location']].copy()

        different.columns=dualfields+['md5_hash','filename','location']
        # our different list will have multiple entries for a workflow if there is a version on either side
        # we want to grab the most recent one, so we sort and grab the most recent one for each workflow
        changedfiles = different.sort_values('date_created',ascending=False).groupby('filename').first()

        # get an exclusive or list of workflow ids - that is we want lists of files that are
        # on one machine or the other, but not both
        remote_spec_ids = remote_files[['filename']]
        local_spec_ids = local[['filename']]
        left = remote_spec_ids[~remote_spec_ids['filename'].isin(local_spec_ids['filename'])]
        right = local_spec_ids[~local_spec_ids['filename'].isin(remote_spec_ids['filename'])]
        changedfiles['new'] = False
        changedfiles.loc[changedfiles.index.isin(left['filename']), 'new'] = True
        changedfiles.loc[changedfiles.index.isin(right['filename']),'new'] = True
        changedfiles = changedfiles.replace({NA: None})
        # return the list as a dict, let swagger convert it to json
        if as_df:
            return changedfiles
        else:
            return changedfiles.reset_index().to_dict(orient='records')

    @staticmethod
    def get_all_spec_state():
        """
        Return a list of all workflow specs along with last updated date and a
        thumbprint of all of the files that are used for that workflow_spec
        Convert into a dict list from a dataframe
        """
        df = WorkflowSyncService.get_all_spec_state_dataframe()
        return df.reset_index().to_dict(orient='records')

    @staticmethod
    def get_workflow_spec_files(workflow_spec_id):
        """
        Return a list of all workflow specs along with last updated date and a
        thumbprint of all of the files that are used for that workflow_spec
        Convert into a dict list from a dataframe
        """
        df = WorkflowSyncService.get_workflow_spec_files_dataframe(workflow_spec_id)
        return df.reset_index().to_dict(orient='records')

    @staticmethod
    def get_workflow_spec_files_dataframe(workflowid):
        """
        Return a list of all files for a workflow_spec along with last updated date and a
        hash so we can determine file differences for a changed workflow on a box.
        Return a dataframe

        In the special case of "REFERENCE_FILES" we get all of the files that are
        marked as is_reference
        """
        if workflowid == 'REFERENCE_FILES':
            x = session.query(FileDataModel).join(FileModel).filter((FileModel.is_reference == True) &
                                                                    (FileModel.archived!=True))
        else:
            x = session.query(FileDataModel).join(FileModel).filter((FileModel.workflow_spec_id == workflowid) &
                                                                    (FileModel.archived!=True))
        # there might be a cleaner way of getting a data frome from some of the
        # fields in the ORM - but this works OK
        filelist = []
        for file in x:
            filelist.append({'file_model_id':file.file_model_id,
                             'workflow_spec_id': file.file_model.workflow_spec_id,
                             'md5_hash':file.md5_hash,
                             'sha':file.sha,
                             'filename':file.file_model.name,
                             'type':file.file_model.type.name,
                             'primary':file.file_model.primary,
                             'content_type':file.file_model.content_type,
                             'primary_process_id':file.file_model.primary_process_id,
                             'date_created':file.date_created})
        if len(filelist) == 0:
            return pd.DataFrame(columns=['file_model_id',
                                         'workflow_spec_id',
                                         'md5_hash',
                                         'sha',
                                         'filename',
                                         'type',
                                         'primary',
                                         'content_type',
                                         'primary_process_id',
                                         'date_created'])
        df = pd.DataFrame(filelist).sort_values('date_created').groupby('file_model_id').last()
        df['date_created'] = df['date_created'].astype('str')
        return df

    @staticmethod
    def get_all_spec_state_dataframe():
        """
        Return a list of all workflow specs along with last updated date and a
        thumbprint of all of the files that are used for that workflow_spec
        Return a dataframe
        """
        wfs = session.query(WorkflowSpecModel).all()
        file_data = session.query(FileDataModel).join(FileModel).filter(FileModel.archived != True)
        wflookup = {}
        for workflow_spec in wfs:
            wflookup[workflow_spec.id] = workflow_spec.display_name
        # there might be a cleaner way of getting a data from from some of the
        # fields in the ORM - but this works OK
        filelist = []
        for file in file_data:
            filelist.append({'file_model_id':file.file_model_id,
                             'workflow_spec_id': file.file_model.workflow_spec_id,
                             'md5_hash':file.md5_hash,
                             'sha':file.sha,
                             'name':wflookup.get(file.file_model.workflow_spec_id,'reference'),
                             'filename':file.file_model.name,
                             'date_created':file.date_created})
        if len(filelist) == 0:
            df = pd.DataFrame(columns=['file_model_id','workflow_spec_id','md5_hash',
                                       'spec_name','sha','filename',
                                       'date_created'])
        else:
            df = pd.DataFrame(filelist)

        # If the file list is empty, return an empty data frame
        if df.empty:
            return df

        # get a distinct list of file_model_id's with the most recent file_data retained
        df = df.sort_values('date_created').drop_duplicates(['file_model_id'],keep='last').copy()

        # take that list and then group by workflow_spec and retain the most recently touched file
        # and make a consolidated hash of the md5_checksums - this acts as a 'thumbprint' for each
        # workflow spec
        df = df.groupby('workflow_spec_id').agg({'date_created':'max',
                                                 'name': 'max',
                                                 'md5_hash':join_uuids}).copy()
        # get only the columns we are really interested in returning
        df = df[['date_created','md5_hash','name']].copy()
        # convert dates to string
        df['date_created'] = df['date_created'].astype('str')
        return df

    def lookup_status(item,table):
        lookup = ','.join([str(x) for x in item])
        print(lookup)
        matchers = [x for x in table.keys() if re.match(x,lookup)]
        if len(matchers) == 0:
            raise Exception('Expecting at least one match')
        print(matchers)
        return table[matchers[0]]



    def get_explain_text(wf):
        print(wf)
        if wf['status'] == 'keep':
            return spantext(' Will be Kept','green')
        if wf['status'] == 'delete':
            return spantext(' WILL BE DELETED','red')
        if wf['status'] == 'revert':
            return spantext(' WILL BE RESET TO MATCH REMOTE','red')
        if wf['status'] == 'update':
            return spantext(' Will be updated to match remote','yellow')
        if wf['status'] == 'copy':
            return spantext(' Will be copied from remote','green')


    def get_master_list_html(remote,keep_new_local=False):
        categories = WorkflowSyncService.get_master_list(remote,keep_new_local)
        category_list = htm.UL()
        for cat in categories.keys():
            currentcat = htm.LI(cat)
            category_list.extend([currentcat])
            workflow_list = htm.UL()
            currentcat.extend([workflow_list])
            workflows = categories[cat]
            for wf in workflows:
                currentwf = htm.LI(wf['name'])
                wftext = WorkflowSyncService.get_explain_text(wf)
                currentwf.extend([wftext])
                workflow_list.extend([currentwf])
                file_list = htm.UL()
                currentwf.extend([file_list])
                for file in wf['files']:
                    currentfi = htm.LI(file['filename'])
                    wftext = WorkflowSyncService.get_explain_text(file)
                    currentfi.extend([wftext])
                    file_list.extend([currentfi])

        print(etree.tostring(category_list))
        return(etree.tostring(category_list).decode('utf8'))

