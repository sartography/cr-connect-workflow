import copy
import re
from io import BytesIO

import jinja2
from docx.shared import Inches
from docxtpl import DocxTemplate, Listing, InlineImage

from crc import session
from crc.api.common import ApiError
from crc.models.file import CONTENT_TYPES, FileModel, FileDataModel
from crc.models.workflow import WorkflowModel
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
        self.process_template(task, study_id, None, *args, **kwargs)

    def do_task(self, task, study_id, *args, **kwargs):
        workflow_id = task.workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY]
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        final_document_stream = self.process_template(task, study_id, workflow, *args, **kwargs)
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
            # Get the workflow's latest files
            joined_file_data_models = WorkflowProcessor\
                .get_file_models_for_version(workflow.workflow_spec_id, workflow.spec_version)

            for joined_file_data in joined_file_data_models:
                if joined_file_data.file_model.name == file_name:
                    file_data_model = session.query(FileDataModel).filter_by(id=joined_file_data.id).first()

        if workflow is None or file_data_model is None:
            file_data_model = FileService.get_workflow_file_data(task.workflow, file_name)

        # Get images from file/files fields
        if len(args) == 3:
            image_file_data = self.get_image_file_data(args[2], task)
        else:
            image_file_data = None

        return self.make_template(BytesIO(file_data_model.data), task.data, image_file_data)

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

    def make_template(self, binary_stream, context, image_file_data=None):
        doc = DocxTemplate(binary_stream)
        doc_context = copy.deepcopy(context)
        doc_context = self.rich_text_update(doc_context)
        doc_context = self.append_images(doc, doc_context, image_file_data)
        jinja_env = jinja2.Environment(autoescape=True)
        doc.render(doc_context, jinja_env)
        target_stream = BytesIO()
        doc.save(target_stream)
        target_stream.seek(0)  # move to the beginning of the stream.
        return target_stream

    def append_images(self, template, context, image_file_data):
        context['images'] = {}
        if image_file_data is not None:
            for file_data_model in image_file_data:
                fm = file_data_model.file_model
                if fm is not None:
                    context['images'][fm.id] = {
                        'name': fm.name,
                        'url': '/v1.0/file/%s/data' % fm.id,
                        'image': self.make_image(file_data_model, template)
                    }

        return context

    def make_image(self, file_data_model, template):
        return InlineImage(template, BytesIO(file_data_model.data), width=Inches(6.5))

    def rich_text_update(self, context):
        """This is a bit of a hack.  If we find that /n characters exist in the data, we want
        these to come out in the final document without requiring someone to predict it in the
        template.  Ideally we would use the 'RichText' feature of the python-docx library, but
        that requires we both escape it here, and in the Docx template.  There is a thing called
        a 'listing' in python-docx library that only requires we use it on the way in, and the
        template doesn't have to think about it.  So running with that for now."""
        # loop through the content, identify anything that has a newline character in it, and
        # wrap that sucker in a 'listing' function.
        if isinstance(context, dict):
            for k, v in context.items():
                context[k] = self.rich_text_update(v)
        elif isinstance(context, list):
            for i in range(len(context)):
                context[i] = self.rich_text_update(context[i])
        elif isinstance(context, str) and '\n' in context:
            return Listing(context)
        return context
