from crc import session
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.file import FileModel
from crc.models.task_event import TaskEventModel
from crc.scripts.script import Script
from crc.services.document_service import DocumentService
from crc.services.file_service import FileService
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
        doc_code = None
        files_to_delete = []
        if 'task_id' in kwargs:
            task_spec_name = kwargs['task_id']
            if 'doc_code' in kwargs:
                doc_code = kwargs['doc_code']
                if DocumentService.is_allowed_document(doc_code):
                    files_to_delete = session.query(FileModel). \
                        filter(FileModel.workflow_id == workflow_id). \
                        filter(FileModel.task_spec == task_spec_name). \
                        filter(FileModel.irb_doc_code == doc_code).all()
                else:
                    raise ApiError(code='bad_doc_code',
                                   message=f'This is not a valid doc code: {doc_code}')
            else:
                files_to_delete = session.query(FileModel). \
                    filter(FileModel.workflow_id == workflow_id). \
                    filter(FileModel.task_spec == task_spec_name).all()

            # delete files
            for file in files_to_delete:
                FileService().delete_file(file.id)

                # delete the data store
                session.query(DataStoreModel). \
                    filter(DataStoreModel.file_id == file.id).delete()

            # delete task events
            # TODO: This doesn't work.
            # It always deletes all task_events related to the task
            # Don't currently have a way to limit to a specific doc code
            task_event_models = session.query(TaskEventModel). \
                filter(TaskEventModel.workflow_id == workflow_id). \
                filter(TaskEventModel.study_id == study_id). \
                filter(TaskEventModel.task_name == task_spec_name). \
                filter_by(action=WorkflowService.TASK_ACTION_COMPLETE).all()
            # thought about looking into the form_data and deleting parts of it.
            for model in task_event_models:
                form_data = model.form_data
                for item in form_data:
                    if item.value == doc_code:
                        pass

        else:
            raise ApiError(code='missing_task_id',
                           message='The delete_task_file_data requires task_id. This is the ID of the task used to upload the file(s)')

