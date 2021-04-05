from crc import session
from crc.models.file import FileModel
from crc.scripts.script import Script
from crc.services.file_service import FileService


class DeleteIRBDocument(Script):

    def get_description(self):
        return """Delete an IRB document from a workflow"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        pass

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        irb_document = kwargs['irb_document']
        result = session.query(FileModel).filter(FileModel.workflow_id==workflow_id, FileModel.irb_doc_code==irb_document).all()
        for file in result:
            FileService.delete_file(file.id)
