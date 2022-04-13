from crc import session
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.file import DocumentModel
from crc.models.task_event import TaskEventModel
from crc.scripts.script import Script
from crc.services.document_service import DocumentService
from crc.services.user_file_service import UserFileService
from crc.services.workflow_service import WorkflowService


class DeleteTaskData(Script):

    def get_description(self):
        return """Delete IRB Documents and task data from a workflow, for a given task"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if 'task_id' in kwargs:
            return True
        elif len(args) == 1:
            return True
        return False

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        # fixme: using task_id is confusing, this is actually the name of the task_spec

        # make sure we have a task_id
        if 'task_id' in kwargs:
            task_spec_name = kwargs['task_id']
        elif len(args) == 1:
            task_spec_name = args[0]
        else:
            raise ApiError(code='missing_task_id',
                           message='The delete_task_data requires task_id. This is the ID of the task used to upload the file(s)')

        # delete task events
        session.query(TaskEventModel).filter(TaskEventModel.workflow_id == workflow_id).filter(
            TaskEventModel.study_id == study_id).filter(TaskEventModel.task_name == task_spec_name).filter_by(
            action=WorkflowService.TASK_ACTION_COMPLETE).delete()

        files_to_delete = session.query(DocumentModel). \
            filter(DocumentModel.workflow_id == workflow_id). \
            filter(DocumentModel.task_spec == task_spec_name).all()

        # delete files
        for file in files_to_delete:
            UserFileService().delete_file(file.id)

            # delete the data store
            # session.query(DataStoreModel). \
            #     filter(DataStoreModel.file_id == file.id).delete()