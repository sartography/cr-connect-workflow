from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel
from crc.scripts.script import Script
from crc.services.file_service import FileService


class DeleteIRBDocument(Script):

    def get_description(self):
        return """Delete an IRB document from a workflow"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        irb_document = kwargs['irb_document']
        result = session.query(FileModel).filter(
            FileModel.workflow_id == workflow_id, FileModel.irb_doc_code == irb_document).all()
        if result:
            return True
        return False

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        irb_doc_code = kwargs['irb_document']
        if FileService.is_allowed_document(irb_doc_code):
            result = session.query(FileModel).filter(
                FileModel.workflow_id == workflow_id, FileModel.irb_doc_code == irb_doc_code).all()
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], FileModel):
                for file in result:
                    FileService.delete_file(file.id)
            else:
                raise ApiError.from_task(code='no_document_found',
                                         message=f'No document of type {irb_doc_code} was found for this workflow.',
                                         task=task)
        else:
            raise ApiError.from_task(code='invalid_irb_document',
                                     message=f'{irb_doc_code} is not a valid IRB document code',
                                     task=task)
