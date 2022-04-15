from SpiffWorkflow.util.metrics import timeit

from crc.scripts.script import Script
from crc.services.user_file_service import UserFileService


class IsFileUploaded(Script):

    def get_description(self):
        return """Test whether a file is uploaded for a study. 
                  Pass in the IRB Doc Code for the file."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        doc_code = args[0]
        files = UserFileService.get_files_for_study(study_id)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        doc_code = args[0]
        files = UserFileService.get_files_for_study(study_id, irb_doc_code=doc_code)
        for file in files:
            if file.archived is False:
                return True
        return False
