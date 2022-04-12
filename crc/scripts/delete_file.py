from SpiffWorkflow.exceptions import WorkflowTaskExecException

from crc import session
from crc.api.common import ApiError
from crc.models.file import DocumentModel
from crc.scripts.script import Script
from crc.services.document_service import DocumentService
from crc.services.user_file_service import UserFileService


class DeleteFile(Script):

    @staticmethod
    def process_document_deletion(doc_code, workflow_id, task):
        if DocumentService.is_allowed_document(doc_code):
            result = session.query(DocumentModel).filter(
                DocumentModel.workflow_id == workflow_id, DocumentModel.irb_doc_code == doc_code).all()
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], DocumentModel):
                for file in result:
                    UserFileService.delete_file(file.id)
            else:
                raise WorkflowTaskExecException(task, f'delete_file() failed. No document of type {doc_code}'
                                                      f' was found for this workflow.')

        else:
            raise WorkflowTaskExecException(task, f'delete_file() failed. {doc_code} is not  valid document code.')

    def get_codes(self, task, args, kwargs):
        if 'code' in kwargs:
            if isinstance(kwargs['code'], list):
                codes = kwargs['code']
            else:
                codes = [kwargs['code']]
        else:
            codes = []
            for arg in args:
                if isinstance(arg, list):
                    codes.extend(arg)
                else:
                    codes.append(arg)

        if codes is None or len(codes) == 0:
            raise WorkflowTaskExecException(task, f'delete_file() failed. Please provide a document code.')

        return codes

    def get_description(self):
        return """Delete an IRB document from a workflow"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        doc_codes = self.get_codes(task, args, kwargs)
        for code in doc_codes:
            result = session.query(DocumentModel).filter(
                DocumentModel.workflow_id == workflow_id, DocumentModel.irb_doc_code == code).all()
            if not result:
                return False
        return True

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        doc_codes = self.get_codes(task, args, kwargs)
        for doc_code in doc_codes:
            self.process_document_deletion(doc_code, workflow_id, task)
