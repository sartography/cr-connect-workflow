from crc.scripts.script import Script
from crc.services.file_service import FileService


class IsFileUploaded(Script):

    def get_description(self):
        return """Test whether a file is uploaded for a study. 
                  Pass in the IRB Doc Code for the file."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        doc_code = args[0]
        files = FileService.get_files_for_study(study_id)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        files = FileService.get_files_for_study(study_id)
        if len(files) > 0:
            doc_code = args[0]
            for file in files:
                if doc_code == file.irb_doc_code:
                    return True
        return False
