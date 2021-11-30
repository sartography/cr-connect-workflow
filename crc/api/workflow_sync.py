from crc import app
from crc.api.common import ApiError
from crc.api.workflow import get_workflow_specification
from crc.models.file import FileModelSchema, FileDataModelSchema
from crc.models.sync import SyncWorkflowSchema
from crc.services.workflow_sync import WorkflowSyncService

from flask import request


def get_sync_workflow_specification(workflow_spec_id):
    """
    NB - this is exactly the same as the workflow API, but it uses a different
         authentication Method. I tried to combine this into ONE api call that used multiple authentication scemes
         and it didn't work at all - I've added this as ticket #
    """
    return get_workflow_specification(workflow_spec_id)


def verify_token(token, required_scopes):
    """
    Part of the Swagger API permissions for the syncing API
    The env variable for this is defined in config/default.py

    If you are 'playing' with the swagger interface, you will want to copy the
    token that is defined there and use it to authenticate the API if you are
    emulating copying files between systems.
    """
    if token == app.config['API_TOKEN']:
        return {'scope': ['any']}
    else:
        raise ApiError("permission_denied", "API Token information is not correct")


def get_sync_sources():
    sync_sources = WorkflowSyncService.get_sync_sources()
    return sync_sources


def sync_all_changed_workflows(remote, keep_new_local=False):
    result = WorkflowSyncService.sync_all_changed_workflows(remote, keep_new_local)
    return result


def get_master_list(remote, keep_new_local=False):
    master_list = WorkflowSyncService.get_master_list(remote, keep_new_local)
    return master_list


def get_changed_workflows(remote, as_df=False, keep_new_local=False):
    changed_workflows = WorkflowSyncService.get_changed_workflows(remote, as_df, keep_new_local)
    return changed_workflows


def sync_changed_files(remote, workflow_spec_id):
    changed_files = WorkflowSyncService.sync_changed_files(remote,workflow_spec_id)
    return changed_files


def get_changed_files(remote,workflow_spec_id,as_df=False):
    changed_files = WorkflowSyncService.get_changed_files(remote,workflow_spec_id,as_df)
    return changed_files


def get_all_spec_state():
    all_spec_state = WorkflowSyncService.get_all_spec_state()
    return SyncWorkflowSchema(many=True).dump(all_spec_state)
    # return all_spec_state


def get_workflow_spec_files(workflow_spec_id):
    workflow_spec_files = WorkflowSyncService.get_workflow_spec_files(workflow_spec_id)
    file_data_models = FileDataModelSchema(many=True).dump(workflow_spec_files)
    return file_data_models
