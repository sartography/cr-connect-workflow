from io import StringIO, BytesIO

from jinja2 import UndefinedError

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel
from crc.models.workflow import WorkflowSpecModel
from docxtpl import DocxTemplate
import jinja2

from crc.services.FileService import FileService
from crc.services.workflow_processor import WorkflowProcessor


class CompleteTemplate(object):
    """Completes a word template, using the data available in the current task. Heavy on the
    error messages, because there is so much that can go wrong here, and we want to provide
    as much feedback as possible.  Some of this might move up to a higher level object or be
    passed into all tasks as we complete more work."""


    def do_task(self, task, *args, **kwargs):
        """Entry point, mostly worried about wiring it all up."""
        if len(args) != 1:
            raise ApiError(code="missing_argument",
                           message="The CompleteTask script requires a single argument with "
                                   "the name of the docx template to use.")
        file_name = args[0]
        workflow_spec_model = self.find_spec_model_in_db(task.workflow)

        if workflow_spec_model is None:
            raise ApiError(code="workflow_model_error",
                           message="Something is wrong.  I can't find the workflow you are using.")

        file_data_model = session.query(FileDataModel) \
            .join(FileModel) \
            .filter(FileModel.name == file_name) \
            .filter(FileModel.workflow_spec_id == workflow_spec_model.id).first()


        if file_data_model is None:
            raise ApiError(code="file_missing",
                           message="Can not find a file called '%s' "
                                   "within workflow specification '%s'") % (args[0], workflow_spec_model.id)

        final_document_stream = self.make_template(file_data_model, task.data)
        study_id = task.workflow.data[WorkflowProcessor.STUDY_ID_KEY]
        workflow_id = task.workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY]
        FileService.add_task_file(study_id=study_id, workflow_id=workflow_id, task_id=task.id,
                                  name=file_name,
                                  content_type=FileService.DOCX_MIME,
                                  binary_data=final_document_stream.read())

        print("Complete Task was called with %s" % str(args))

    def make_template(self, file_data_model, context):
        doc = DocxTemplate(BytesIO(file_data_model.data))
        jinja_env = jinja2.Environment(autoescape=True)
        doc.render(context, jinja_env)
        target_stream = BytesIO()
        doc.save(target_stream)
        target_stream.seek(0) # move to the beginning of the stream.
        return target_stream

    def find_spec_model_in_db(self, workflow):
        """ Search for the workflow """
        # When the workflow spec model is created, we record the primary process id,
        # then we can look it up.  As there is the potential for sub-workflows, we
        # may need to travel up to locate the primary process.
        spec = workflow.spec
        workflow_model = session.query(WorkflowSpecModel). \
            filter(WorkflowSpecModel.primary_process_id == spec.name).first()
        if workflow_model is None and workflow != workflow.outer_workflow:
            return self.find_spec_model_in_db(workflow.outer_workflow)

        return workflow_model
