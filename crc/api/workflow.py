import hashlib
import json
import uuid
from io import StringIO
from hashlib import md5

import pandas as pd
from SpiffWorkflow.util.deep_merge import DeepMerge
from flask import g
from crc import session, db, app
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.api_models import WorkflowApi, WorkflowApiSchema, NavigationItem, NavigationItemSchema
from crc.models.file import FileModel, LookupDataSchema, FileDataModel
from crc.models.study import StudyModel, WorkflowMetadata
from crc.models.task_event import TaskEventModel, TaskEventModelSchema, TaskEvent, TaskEventSchema
from crc.models.workflow import WorkflowModel, WorkflowSpecModelSchema, WorkflowSpecModel, WorkflowSpecCategoryModel, \
    WorkflowSpecCategoryModelSchema
from crc.services.file_service import FileService
from crc.services.lookup_service import LookupService
from crc.services.study_service import StudyService
from crc.services.user_service import UserService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from flask_cors import cross_origin
import requests

def all_specifications():
    schema = WorkflowSpecModelSchema(many=True)
    return schema.dump(session.query(WorkflowSpecModel).all())


def add_workflow_specification(body):
    new_spec: WorkflowSpecModel = WorkflowSpecModelSchema().load(body, session=session)
    session.add(new_spec)
    session.commit()
    return WorkflowSpecModelSchema().dump(new_spec)


def get_workflow_specification(spec_id):
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')

    spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        raise ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')

    return WorkflowSpecModelSchema().dump(spec)


def validate_workflow_specification(spec_id):
    errors = []
    try:
        WorkflowService.test_spec(spec_id)
    except ApiError as ae:
        ae.message = "When populating all fields ... " + ae.message
        errors.append(ae)
    try:
        # Run the validation twice, the second time, just populate the required fields.
        WorkflowService.test_spec(spec_id, required_only=True)
    except ApiError as ae:
        ae.message = "When populating only required fields ... " + ae.message
        errors.append(ae)
    return ApiErrorSchema(many=True).dump(errors)


def update_workflow_specification(spec_id, body):
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Spec ID.')
    spec = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        raise ApiError('unknown_study', 'The spec "' + spec_id + '" is not recognized.')

    schema = WorkflowSpecModelSchema()
    spec = schema.load(body, session=session, instance=spec, partial=True)
    session.add(spec)
    session.commit()
    return schema.dump(spec)


def delete_workflow_specification(spec_id):
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')

    spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        raise ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')

    # Delete all items in the database related to the deleted workflow spec.
    files = session.query(FileModel).filter_by(workflow_spec_id=spec_id).all()
    for file in files:
        FileService.delete_file(file.id)

    session.query(TaskEventModel).filter(TaskEventModel.workflow_spec_id == spec_id).delete()

    # Delete all events and workflow models related to this specification
    for workflow in session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id):
        StudyService.delete_workflow(workflow.id)
    session.query(WorkflowSpecModel).filter_by(id=spec_id).delete()
    session.commit()


def get_workflow(workflow_id, soft_reset=False, hard_reset=False, do_engine_steps=True):
    """Soft reset will attempt to update to the latest spec without starting over,
    Hard reset will update to the latest spec and start from the beginning.
    Read Only will return the workflow in a read only state, without running any
    engine tasks or logging any events. """
    workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model, soft_reset=soft_reset, hard_reset=hard_reset)
    if do_engine_steps:
        processor.do_engine_steps()
        processor.save()
        WorkflowService.update_task_assignments(processor)
    workflow_api_model = WorkflowService.processor_to_workflow_api(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def get_task_events(action = None, workflow = None, study = None):
    """Provides a way to see a history of what has happened, or get a list of tasks that need your attention."""
    query = session.query(TaskEventModel).filter(TaskEventModel.user_uid == g.user.uid)
    if action:
        query = query.filter(TaskEventModel.action == action)
    if workflow:
        query = query.filter(TaskEventModel.workflow_id == workflow)
    if study:
        query = query.filter(TaskEventModel.study_id == study)
    events = query.all()

    # Turn the database records into something a little richer for the UI to use.
    task_events = []
    for event in events:
        study = session.query(StudyModel).filter(StudyModel.id == event.study_id).first()
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == event.workflow_id).first()
        workflow_meta = WorkflowMetadata.from_workflow(workflow)
        task_events.append(TaskEvent(event, study, workflow_meta))
    return TaskEventSchema(many=True).dump(task_events)


def delete_workflow(workflow_id):
    StudyService.delete_workflow(workflow_id)


def set_current_task(workflow_id, task_id):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    spiff_task = processor.bpmn_workflow.get_task(task_id)
    _verify_user_and_role(processor, spiff_task)
    user_uid = UserService.current_user(allow_admin_impersonate=True).uid
    if spiff_task.state != spiff_task.COMPLETED and spiff_task.state != spiff_task.READY:
        raise ApiError("invalid_state", "You may not move the token to a task who's state is not "
                                        "currently set to COMPLETE or READY.")

    # If we have an interrupt task, run it.
    processor.bpmn_workflow.cancel_notify()

    # Only reset the token if the task doesn't already have it.
    if spiff_task.state == spiff_task.COMPLETED:
        spiff_task.reset_token(reset_data=True)  # Don't try to copy the existing data back into this task.

    processor.save()
    WorkflowService.log_task_action(user_uid, processor, spiff_task, WorkflowService.TASK_ACTION_TOKEN_RESET)
    WorkflowService.update_task_assignments(processor)

    workflow_api_model = WorkflowService.processor_to_workflow_api(processor, spiff_task)
    return WorkflowApiSchema().dump(workflow_api_model)


def update_task(workflow_id, task_id, body, terminate_loop=None):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    if workflow_model is None:
        raise ApiError("invalid_workflow_id", "The given workflow id is not valid.", status_code=404)

    elif workflow_model.study is None:
        raise ApiError("invalid_study", "There is no study associated with the given workflow.", status_code=404)

    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    spiff_task = processor.bpmn_workflow.get_task(task_id)
    _verify_user_and_role(processor, spiff_task)
    if not spiff_task:
        raise ApiError("empty_task", "Processor failed to obtain task.", status_code=404)
    if spiff_task.state != spiff_task.READY:
        raise ApiError("invalid_state", "You may not update a task unless it is in the READY state. "
                                        "Consider calling a token reset to make this task Ready.")

    if terminate_loop:
        spiff_task.terminate_loop()
    spiff_task.update_data(body)
    processor.complete_task(spiff_task)
    processor.do_engine_steps()
    processor.save()

    # Log the action, and any pending task assignments in the event of lanes in the workflow.
    user = UserService.current_user(allow_admin_impersonate=False) # Always log as the real user.
    WorkflowService.log_task_action(user.uid, processor, spiff_task, WorkflowService.TASK_ACTION_COMPLETE)
    WorkflowService.update_task_assignments(processor)

    workflow_api_model = WorkflowService.processor_to_workflow_api(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def list_workflow_spec_categories():
    schema = WorkflowSpecCategoryModelSchema(many=True)
    return schema.dump(session.query(WorkflowSpecCategoryModel).all())


def get_workflow_spec_category(cat_id):
    schema = WorkflowSpecCategoryModelSchema()
    return schema.dump(session.query(WorkflowSpecCategoryModel).filter_by(id=cat_id).first())


def add_workflow_spec_category(body):
    schema = WorkflowSpecCategoryModelSchema()
    new_cat: WorkflowSpecCategoryModel = schema.load(body, session=session)
    session.add(new_cat)
    session.commit()
    return schema.dump(new_cat)


def update_workflow_spec_category(cat_id, body):
    if cat_id is None:
        raise ApiError('unknown_category', 'Please provide a valid Workflow Spec Category ID.')

    category = session.query(WorkflowSpecCategoryModel).filter_by(id=cat_id).first()

    if category is None:
        raise ApiError('unknown_category', 'The category "' + cat_id + '" is not recognized.')

    schema = WorkflowSpecCategoryModelSchema()
    category = schema.load(body, session=session, instance=category, partial=True)
    session.add(category)
    session.commit()
    return schema.dump(category)


def delete_workflow_spec_category(cat_id):
    session.query(WorkflowSpecCategoryModel).filter_by(id=cat_id).delete()
    session.commit()


def lookup(workflow_id, field_id, query=None, value=None, limit=10):
    """
    given a field in a task, attempts to find the lookup table or function associated
    with that field and runs a full-text query against it to locate the values and
    labels that would be returned to a type-ahead box.
    Tries to be fast, but first runs will be very slow.
    """
    workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
    lookup_data = LookupService.lookup(workflow, field_id, query, value, limit)
    return LookupDataSchema(many=True).dump(lookup_data)


def _verify_user_and_role(processor, spiff_task):
    """Assures the currently logged in user can access the given workflow and task, or
    raises an error.  """

    user = UserService.current_user(allow_admin_impersonate=True)
    allowed_users = WorkflowService.get_users_assigned_to_task(processor, spiff_task)
    if user.uid not in allowed_users:
        raise ApiError.from_task("permission_denied",
                                 f"This task must be completed by '{allowed_users}', "
                                 f"but you are {user.uid}", spiff_task)
def join_uuids(uuids):
    """Joins a pandas Series of uuids and combines them in one hash"""
    combined_uuids = ''.join([str(uuid) for uuid in uuids.sort_values()]) # ensure that values are always
                                                                          # in the same order
    return hashlib.md5(combined_uuids.encode('utf8')).hexdigest() # make a hash of the hashes

def verify_token(token, required_scopes):
    if token == app.config['API_TOKEN']:
        return {'scope':['any']}
    else:
        raise ApiError("permission_denied","API Token information is not correct")


def get_changed_workflows(remote,as_df=False):
    """
    gets a remote endpoint - gets the workflows and then
    determines what workflows are different from the remote endpoint
    """
    response = requests.get('http://'+remote+'/v1.0/workflow_spec/all',headers={'X-CR-API-KEY':app.config['API_TOKEN']})

    # This is probably very and may allow cross site attacks - fix later
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
    workflows = workflowsdf.reset_index().to_dict(orient='records')
    for workflow in workflows:
        sync_changed_files(remote,workflow['workflow_spec_id'])
    return [x['workflow_spec_id'] for x in workflows]


def sync_changed_files(remote,workflow_spec_id):
    # make sure that spec is local before syncing files
    remotespectext  =  requests.get('http://'+remote+'/v1.0/workflow-specification/'+workflow_spec_id,
                                    headers={'X-CR-API-KEY': app.config['API_TOKEN']})
    specdict = json.loads(remotespectext.text)
    localspec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == workflow_spec_id).first()
    if localspec is None:
        localspec = WorkflowSpecModel()
        localspec.id = workflow_spec_id
    if specdict['category'] == None:
        localspec.category = None
    else:
        localspec.category = session.query(WorkflowSpecCategoryModel).filter(WorkflowSpecCategoryModel.id
                                                                         == specdict['category']['id']).first()
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
        FileService.delete_file(currentfile.id)

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

        response = requests.get('http://'+remote+'/v1.0/file/'+updatefile['md5_hash']+'/hash_data',
                                headers={'X-CR-API-KEY': app.config['API_TOKEN']})
        FileService.update_file(currentfile,response.content,updatefile['type'])
    session.commit()
    return [x['filename'] for x in updatefiles]


def get_changed_files(remote,workflow_spec_id,as_df=False):
    """
    gets a remote endpoint - gets the files for a workflow_spec on both
    local and remote and determines what files have been change and returns a list of those
    files
    """
    response = requests.get('http://'+remote+'/v1.0/workflow_spec/'+workflow_spec_id+'/files',
                            headers={'X-CR-API-KEY':app.config['API_TOKEN']})
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

