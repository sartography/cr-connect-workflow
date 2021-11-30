import re
from io import BytesIO

from SpiffWorkflow.exceptions import WorkflowTaskExecException

from crc import session
from crc.api.common import ApiError
from crc.models.file import CONTENT_TYPES, FileModel
from crc.models.workflow import WorkflowModel
from crc.scripts.script import Script
from crc.services.file_service import FileService
from crc.services.jinja_service import JinjaService
from crc.services.workflow_processor import WorkflowProcessor


class CompleteTemplate(Script):

    def get_description(self):
        return """Using the Jinja template engine, takes data available in the current task, and uses it to populate 
a word document that contains Jinja markup.  Please see https://docxtpl.readthedocs.io/en/latest/ 
for more information on exact syntax.
Takes two arguments:
1. The name of a MS Word docx file to use as a template.
2. The 'code' of the IRB Document as set in the irb_documents.xlsx file."
"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        """For validation only, process the template, but do not store it in the database."""
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        self.process_template(task, study_id, workflow, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        final_document_stream = self.process_template(task, study_id, workflow, *args, **kwargs)
        file_name = args[0]
        irb_doc_code = args[1]
        FileService.add_workflow_file(workflow_id=workflow_id,
                                      task_spec_name=task.get_name(),
                                      name=file_name,
                                      content_type=CONTENT_TYPES['docx'],
                                      binary_data=final_document_stream.read(),
                                      irb_doc_code=irb_doc_code)

    def process_template(self, task, study_id, workflow=None, *args, **kwargs):
        """Entry point, mostly worried about wiring it all up."""
        if len(args) < 2 or len(args) > 3:
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

        file_data_model = None
        if workflow is not None:
            # Get the workflow specification file with the given name.
            file_data_models = FileService.get_spec_data_files(
                workflow_spec_id=workflow.workflow_spec_id,
                workflow_id=workflow.id,
                name=file_name)
            if len(file_data_models) > 0:
                file_data_model = file_data_models[0]
            else:
                raise ApiError(code="invalid_argument",
                               message="Uable to locate a file with the given name.")

        # Get images from file/files fields
        if len(args) == 3:
            image_file_data = self.get_image_file_data(args[2], task)
        else:
            image_file_data = None

        try:
            return JinjaService().make_template(BytesIO(file_data_model.data), task.data, image_file_data)
        except ApiError as ae:
            # In some cases we want to provide a very specific error, that does not get obscured when going
            # through the python expression engine. We can do that by throwing a WorkflowTaskExecException,
            # which the expression engine should just pass through.
            raise WorkflowTaskExecException(task, ae.message, exception=ae, line_number=ae.line_number,
                                            error_line=ae.error_line)

    def get_image_file_data(self, fields_str, task):
        image_file_data = []
        images_field_str = re.sub(r'[\[\]]', '', fields_str)
        images_field_keys = [v.strip() for v in images_field_str.strip().split(',')]
        for field_key in images_field_keys:
            if field_key in task.data:
                v = task.data[field_key]
                file_ids = v if isinstance(v, list) else [v]

                for file_id in file_ids:
                    if isinstance(file_id, str) and file_id.isnumeric():
                        file_id = int(file_id)

                    if file_id is not None and isinstance(file_id, int):
                        if not task.workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY]:
                            # Get the actual image data
                            image_file_model = session.query(FileModel).filter_by(id=file_id).first()
                            image_file_data_model = FileService.get_file_data(file_id, image_file_model)
                            if image_file_data_model is not None:
                                image_file_data.append(image_file_data_model)

                    else:
                        raise ApiError(
                            code="not_a_file_id",
                            message="The CompleteTemplate script requires 2-3 arguments. The third argument should "
                                    "be a comma-delimited list of File IDs")

        return image_file_data
