from crc import session
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
        if 'task_id' in kwargs:
            task_id = kwargs['task_id']
        elif len(args) == 1:
            task_id = args[0]

        # Build list of files to delete
        files_to_delete = []
        task_events = session.query(TaskEventModel).filter(TaskEventModel.workflow_id==workflow_id).filter(TaskEventModel.study_id==study_id).filter(TaskEventModel.task_name==task_id).filter_by(action=WorkflowService.TASK_ACTION_COMPLETE).all()
        for task_event in task_events:
            for item in task_event.form_data:
                if DocumentService.is_allowed_document(item):
                    irb_doc_code = item
                    files = session.query(FileModel).filter(FileModel.workflow_id==workflow_id).filter(FileModel.irb_doc_code==irb_doc_code).all()
                    for file in files:
                        if file.id not in files_to_delete:
                            files_to_delete.append(file.id)

        # delete files and data store
        for file in files_to_delete:
            FileService().delete_file(file)

        # delete task events
        session.query(TaskEventModel).filter(TaskEventModel.workflow_id == workflow_id).filter(
            TaskEventModel.study_id == study_id).filter(TaskEventModel.task_name == task_id).filter_by(
            action=WorkflowService.TASK_ACTION_COMPLETE).delete()
