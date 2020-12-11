import hashlib
import json
import pandas as pd
import requests
from crc import session, app
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel
from crc.services.file_service import FileService


def join_uuids(uuids):
    """Joins a pandas Series of uuids and combines them in one hash"""
    combined_uuids = ''.join([str(uuid) for uuid in uuids.sort_values()]) # ensure that values are always
                                                                          # in the same order
    return hashlib.md5(combined_uuids.encode('utf8')).hexdigest() # make a hash of the hashes

def verify_token(token, required_scopes):
    if token == app.config['API_TOKEN']:
        return {'scope':['any']}
    else:
        raise ApiError("permission_denied", "API Token information is not correct")


def get_changed_workflows(remote,as_df=False):
    """
    gets a remote endpoint - gets the workflows and then
    determines what workflows are different from the remote endpoint
    """
    try:
        response = requests.get('http://'+remote+'/v1.0/workflow_sync/all',headers={'X-CR-API-KEY':app.config['API_TOKEN']})
    except:
        raise ApiError("endpoint error", 'had a problem connecting to '+remote)
    if not response.ok:
        raise ApiError("endpoint error", response.text)

    remote = pd.DataFrame(json.loads(response.text))

    # get the local thumbprints & make sure that 'workflow_spec_id' is a column, not an index
    local = get_all_spec_state_dataframe().reset_index()

    # merge these on workflow spec id and hash - this will
    # make two different date columns date_x and date_y
    different  = remote.merge(local,
                              right_on=['workflow_spec_id','md5_hash'],
                              left_on=['workflow_spec_id','md5_hash'],
                              how = 'outer' ,
                              indicator=True).loc[lambda x : x['_merge']!='both']
    if len(different)==0:
        return []
    # each line has a tag on it - if was in the left or the right,
    # label it so we know if that was on the remote or local machine
    different.loc[different['_merge']=='left_only','location'] = 'remote'
    different.loc[different['_merge']=='right_only','location'] = 'local'

    # this takes the different date_created_x and date-created_y columns and
    # combines them back into one date_created column
    index = different['date_created_x'].isnull()
    different.loc[index,'date_created_x'] = different[index]['date_created_y']
    different = different[['workflow_spec_id','date_created_x','location']].copy()
    different.columns=['workflow_spec_id','date_created','location']

    # our different list will have multiple entries for a workflow if there is a version on either side
    # we want to grab the most recent one, so we sort and grab the most recent one for each workflow
    changedfiles = different.sort_values('date_created',ascending=False).groupby('workflow_spec_id').first()

    # get an exclusive or list of workflow ids - that is we want lists of files that are
    # on one machine or the other, but not both
    remote_spec_ids = remote[['workflow_spec_id']]
    local_spec_ids = local[['workflow_spec_id']]
    left = remote_spec_ids[~remote_spec_ids['workflow_spec_id'].isin(local_spec_ids['workflow_spec_id'])]
    right = local_spec_ids[~local_spec_ids['workflow_spec_id'].isin(remote_spec_ids['workflow_spec_id'])]

    # flag files as new that are only on the remote box and remove the files that are only on the local box
    changedfiles['new'] = False
    changedfiles.loc[changedfiles.index.isin(left['workflow_spec_id']), 'new'] = True
    output = changedfiles[~changedfiles.index.isin(right['workflow_spec_id'])]

    # return the list as a dict, let swagger convert it to json
    if as_df:
        return output
    else:
        return output.reset_index().to_dict(orient='records')


def sync_all_changed_workflows(remote):

    workflowsdf = get_changed_workflows(remote,as_df=True)
    if len(workflowsdf) ==0:
        return []
    workflows = workflowsdf.reset_index().to_dict(orient='records')
    for workflow in workflows:
        sync_changed_files(remote,workflow['workflow_spec_id'])
    return [x['workflow_spec_id'] for x in workflows]


def sync_changed_files(remote,workflow_spec_id):
    # make sure that spec is local before syncing files
    try:
        remotespectext  =  requests.get('http://'+remote+'/v1.0/workflow-specification/'+workflow_spec_id,
                                    headers={'X-CR-API-KEY': app.config['API_TOKEN']})
    except:
        raise ApiError("endpoint error", 'had a problem connecting to '+remote)

    if not remotespectext.ok:
        raise ApiError("endpoint error", response.text)

    specdict = json.loads(remotespectext.text)

    localspec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == workflow_spec_id).first()
    if localspec is None:
        localspec = WorkflowSpecModel()
        localspec.id = workflow_spec_id
    if specdict['category'] == None:
        localspec.category = None
    else:
        localcategory = session.query(WorkflowSpecCategoryModel).filter(WorkflowSpecCategoryModel.name
                                                                        == specdict['category']['name']).first()
        if localcategory == None:
            #category doesn't exist - lets make it
            localcategory = WorkflowSpecCategoryModel()
            localcategory.name = specdict['category']['name']
            localcategory.display_name = specdict['category']['display_name']
            localcategory.display_order = specdict['category']['display_order']
            session.add(localcategory)
        localspec.category = localcategory

    localspec.display_order = specdict['display_order']
    localspec.display_name = specdict['display_name']
    localspec.name = specdict['name']
    localspec.description = specdict['description']
    session.add(localspec)

    changedfiles = get_changed_files(remote,workflow_spec_id,as_df=True)
    if len(changedfiles)==0:
        return []
    updatefiles = changedfiles[~((changedfiles['new']==True) & (changedfiles['location']=='local'))]
    updatefiles = updatefiles.reset_index().to_dict(orient='records')

    deletefiles = changedfiles[((changedfiles['new']==True) & (changedfiles['location']=='local'))]
    deletefiles = deletefiles.reset_index().to_dict(orient='records')

    for delfile in deletefiles:
        currentfile = session.query(FileModel).filter(FileModel.workflow_spec_id==workflow_spec_id,
                                            FileModel.name == delfile['filename']).first()

        # it is more appropriate to archive the file than delete
        # due to the fact that we might have workflows that are using the
        # file data
        currentfile.archived = True
        session.add(currentfile)

    for updatefile in updatefiles:
        currentfile = session.query(FileModel).filter(FileModel.workflow_spec_id==workflow_spec_id,
                                            FileModel.name == updatefile['filename']).first()
        if not currentfile:
            currentfile = FileModel()
            currentfile.name = updatefile['filename']
            currentfile.workflow_spec_id = workflow_spec_id

        currentfile.date_created = updatefile['date_created']
        currentfile.type = updatefile['type']
        currentfile.primary = updatefile['primary']
        currentfile.content_type = updatefile['content_type']
        currentfile.primary_process_id = updatefile['primary_process_id']
        session.add(currentfile)
        try:
            response = requests.get('http://'+remote+'/v1.0/file/'+updatefile['md5_hash']+'/hash_data',
                                headers={'X-CR-API-KEY': app.config['API_TOKEN']})
        except:
            raise ApiError("endpoint error", 'had a problem connecting to ' + remote)

        if not response.ok:
            raise ApiError("endpoint error", response.text)

        FileService.update_file(currentfile,response.content,updatefile['type'])
    session.commit()
    return [x['filename'] for x in updatefiles]


def get_changed_files(remote,workflow_spec_id,as_df=False):
    """
    gets a remote endpoint - gets the files for a workflow_spec on both
    local and remote and determines what files have been change and returns a list of those
    files
    """
    try:
        response = requests.get('http://'+remote+'/v1.0/workflow_sync/'+workflow_spec_id+'/files',
                            headers={'X-CR-API-KEY':app.config['API_TOKEN']})
    except:
        raise ApiError("endpoint error", 'had a problem connecting to '+remote)

    if not response.ok:
        raise ApiError("endpoint error", response.text)

    # This is probably very and may allow cross site attacks - fix later
    remote = pd.DataFrame(json.loads(response.text))
    # get the local thumbprints & make sure that 'workflow_spec_id' is a column, not an index
    local = get_workflow_spec_files_dataframe(workflow_spec_id).reset_index()
    local['md5_hash'] = local['md5_hash'].astype('str')
    different = remote.merge(local,
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
    remote_spec_ids = remote[['filename']]
    local_spec_ids = local[['filename']]
    left = remote_spec_ids[~remote_spec_ids['filename'].isin(local_spec_ids['filename'])]
    right = local_spec_ids[~local_spec_ids['filename'].isin(remote_spec_ids['filename'])]
    changedfiles['new'] = False
    changedfiles.loc[changedfiles.index.isin(left['filename']), 'new'] = True
    changedfiles.loc[changedfiles.index.isin(right['filename']),'new'] = True
    changedfiles = changedfiles.replace({pd.np.nan: None})
    # return the list as a dict, let swagger convert it to json
    if as_df:
        return changedfiles
    else:
        return changedfiles.reset_index().to_dict(orient='records')



def get_all_spec_state():
    """
    Return a list of all workflow specs along with last updated date and a
    thumbprint of all of the files that are used for that workflow_spec
    Convert into a dict list from a dataframe
    """
    df = get_all_spec_state_dataframe()
    return df.reset_index().to_dict(orient='records')


def get_workflow_spec_files(workflow_spec_id):
    """
    Return a list of all workflow specs along with last updated date and a
    thumbprint of all of the files that are used for that workflow_spec
    Convert into a dict list from a dataframe
    """
    df = get_workflow_spec_files_dataframe(workflow_spec_id)
    return df.reset_index().to_dict(orient='records')


def get_workflow_spec_files_dataframe(workflowid):
    """
    Return a list of all files for a workflow_spec along with last updated date and a
    hash so we can determine file differences for a changed workflow on a box.
    Return a dataframe
    """
    x = session.query(FileDataModel).join(FileModel).filter(FileModel.workflow_spec_id==workflowid)
    # there might be a cleaner way of getting a data frome from some of the
    # fields in the ORM - but this works OK
    filelist = []
    for file in x:
        filelist.append({'file_model_id':file.file_model_id,
                         'workflow_spec_id': file.file_model.workflow_spec_id,
                         'md5_hash':file.md5_hash,
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
                                     'filename',
                                     'type',
                                     'primary',
                                     'content_type',
                                     'primary_process_id',
                                     'date_created'])
    df = pd.DataFrame(filelist).sort_values('date_created').groupby('file_model_id').last()
    df['date_created'] = df['date_created'].astype('str')
    return df



def get_all_spec_state_dataframe():
    """
    Return a list of all workflow specs along with last updated date and a
    thumbprint of all of the files that are used for that workflow_spec
    Return a dataframe
    """
    x = session.query(FileDataModel).join(FileModel)
    # there might be a cleaner way of getting a data frome from some of the
    # fields in the ORM - but this works OK
    filelist = []
    for file in x:
        filelist.append({'file_model_id':file.file_model_id,
                         'workflow_spec_id': file.file_model.workflow_spec_id,
                         'md5_hash':file.md5_hash,
                         'filename':file.file_model.name,
                         'date_created':file.date_created})
    df = pd.DataFrame(filelist)

    # get a distinct list of file_model_id's with the most recent file_data retained
    df = df.sort_values('date_created').drop_duplicates(['file_model_id'],keep='last').copy()

    # take that list and then group by workflow_spec and retain the most recently touched file
    # and make a consolidated hash of the md5_checksums - this acts as a 'thumbprint' for each
    # workflow spec
    df = df.groupby('workflow_spec_id').agg({'date_created':'max',
                                             'md5_hash':join_uuids}).copy()
    # get only the columns we are really interested in returning
    df = df[['date_created','md5_hash']].copy()
    # convert dates to string
    df['date_created'] = df['date_created'].astype('str')
    return df

