from io import StringIO, BytesIO

from jinja2 import UndefinedError

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.workflow import WorkflowSpecModel, WorkflowModel
from docxtpl import DocxTemplate
import jinja2

from crc.scripts.script import Script
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor


class CompleteTemplate(Script):

    def get_description(self):
        return """        
Using the Jinja template engine, takes data available in the current task, and uses it to populate 
a word document that contains Jinja markup.  Please see https://docxtpl.readthedocs.io/en/latest/ 
for more information on exact syntax.
Takes two arguments:
1. The name of a MS Word docx file to use as a template.
2. The 'code' of the IRB Document as set in the irb_documents.xlsx file."
"""

    def do_task_validate_only(self, task, study_id, *args, **kwargs):
        """For validation only, process the template, but do not store it in the database."""
        self.process_template(task, study_id, *args, **kwargs)

    def do_task(self, task, study_id, *args, **kwargs):
        workflow_id = task.workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY]
        final_document_stream = self.process_template(task, study_id, *args, **kwargs)
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        file_name = args[0]
        irb_doc_code = args[1]
        FileService.add_task_file(study_id=study_id,
                                  workflow_id=workflow_id,
                                  workflow_spec_id=workflow.workflow_spec_id,
                                  task_id=task.id,
                                  name=file_name,
                                  content_type=CONTENT_TYPES['docx'],
                                  binary_data=final_document_stream.read(),
                                  irb_doc_code=irb_doc_code)

    def process_template(self, task, study_id, *args, **kwargs):
        """Entry point, mostly worried about wiring it all up."""
        if len(args) != 2:
            raise ApiError(code="missing_argument",
                           message="The CompleteTemplate script requires 2 arguments.  The first argument is "
                                   "the name of the docx template to use.  The second "
                                   "argument is a code for the document, as "
                                   "set in the reference document %s. " % FileService.DOCUMENT_LIST)
        task_study_id = task.workflow.data[WorkflowProcessor.STUDY_ID_KEY]
        file_name = args[0]

        if task_study_id != study_id:
            raise ApiError(code="invalid_argument",
                           message="The given task does not match the given study.")

        file_data_model = FileService.get_workflow_file_data(task.workflow, file_name)
        return self.make_template(BytesIO(file_data_model.data), task.data)


    def make_template(self, binary_stream, context):
        doc = DocxTemplate(binary_stream)
        jinja_env = jinja2.Environment(autoescape=True)
        doc.render(context, jinja_env)
        target_stream = BytesIO()
        doc.save(target_stream)
        target_stream.seek(0) # move to the beginning of the stream.
        return target_stream


