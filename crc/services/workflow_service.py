from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.MultiInstanceTask import MultiInstanceTask
from SpiffWorkflow.bpmn.specs.NoneTask import NoneTask
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.dmn.specs.BuisnessRuleTask import BusinessRuleTask
from SpiffWorkflow.specs import CancelTask, StartTask
from pandas import ExcelFile

from crc.api.common import ApiError
from crc.models.api_models import Task, MultiInstanceType
import jinja2
from jinja2 import Template

from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor, CustomBpmnScriptEngine
from SpiffWorkflow import Task as SpiffTask, WorkflowException


class WorkflowService(object):
    """Provides tools for processing workflows and tasks.  This
     should at some point, be the only way to work with Workflows, and
     the workflow Processor should be hidden behind this service.
     This will help maintain a structure that avoids circular dependencies.
     But for now, this contains tools for converting spiff-workflow models into our
     own API models with additional information and capabilities."""

    @classmethod
    def test_spec(cls, spec_id):
        """Runs a spec through it's paces to see if it results in any errors.  Not full proof, but a good
        sanity check."""

        spec = WorkflowProcessor.get_spec(spec_id)
        bpmn_workflow = BpmnWorkflow(spec, script_engine=CustomBpmnScriptEngine())
        bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY] = 1
        bpmn_workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY] = spec_id
        bpmn_workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY] = True

        while not bpmn_workflow.is_completed():
            try:
                bpmn_workflow.do_engine_steps()
                tasks = bpmn_workflow.get_tasks(SpiffTask.READY)
                for task in tasks:
                    task_api = WorkflowService.spiff_task_to_api_task(
                        task)  # Assure we try to process the documenation, and raise those errors.
                    WorkflowProcessor.populate_form_with_random_data(task)
                    task.complete()
            except WorkflowException as we:
                raise ApiError.from_task_spec("workflow_execution_exception", str(we),
                                              we.sender)

    @staticmethod
    def spiff_task_to_api_task(spiff_task):
        task_type = spiff_task.task_spec.__class__.__name__

        if isinstance(spiff_task.task_spec, UserTask):
            task_type = "UserTask"
        elif isinstance(spiff_task.task_spec, ManualTask):
            task_type = "ManualTask"
        elif isinstance(spiff_task.task_spec, BusinessRuleTask):
            task_type = "BusinessRuleTask"
        elif isinstance(spiff_task.task_spec, CancelTask):
            task_type = "CancelTask"
        elif isinstance(spiff_task.task_spec, ScriptTask):
            task_type = "ScriptTask"
        elif isinstance(spiff_task.task_spec, StartTask):
            task_type = "StartTask"
        else:
            task_type = "NoneTask"

        info = spiff_task.task_info()
        if info["is_looping"]:
            mi_type = MultiInstanceType.looping
        elif info["is_sequential_mi"]:
            mi_type = MultiInstanceType.sequential
        elif info["is_parallel_mi"]:
            mi_type = MultiInstanceType.parallel
        else:
            mi_type = MultiInstanceType.none

        task = Task(spiff_task.id,
                    spiff_task.task_spec.name,
                    spiff_task.task_spec.description,
                    task_type,
                    spiff_task.get_state_name(),
                    None,
                    "",
                    spiff_task.data,
                    mi_type,
                    info["mi_count"],
                    info["mi_index"])

        # Only process the form and documentation if this is something that is ready or completed.
        if not (spiff_task._is_predicted()):
            if hasattr(spiff_task.task_spec, "form"):
                task.form = spiff_task.task_spec.form
                for field in task.form.fields:
                    WorkflowService._process_options(spiff_task, field)

            task.documentation = WorkflowService._process_documentation(spiff_task)
        return task

    @staticmethod
    def _process_documentation(spiff_task):
        """Runs the given documentation string through the Jinja2 processor to inject data
        create loops, etc...  - If a markdown file exists with the same name as the task id,
        it will use that file instead of the documentation. """

        documentation = spiff_task.task_spec.documentation if hasattr(spiff_task.task_spec, "documentation") else ""

        try:
            doc_file_name = spiff_task.task_spec.name + ".md"
            data_model = FileService.get_workflow_file_data(spiff_task.workflow, doc_file_name)
            raw_doc = data_model.data.decode("utf-8")
        except ApiError:
            raw_doc = documentation

        if not raw_doc:
            return ""

        try:
            template = Template(raw_doc)
            return template.render(**spiff_task.data)
        except jinja2.exceptions.TemplateError as ue:
            raise ApiError(code="template_error", message="Error processing template for task %s: %s" %
                                                          (spiff_task.task_spec.name, str(ue)), status_code=500)
        # TODO:  Catch additional errors and report back.

    @staticmethod
    def _process_options(spiff_task, field):
        """ Checks to see if the options are provided in a separate lookup table associated with the
        workflow, and populates these if possible. """
        if field.has_property(Task.ENUM_OPTIONS_FILE_PROP):
            if not field.has_property(Task.EMUM_OPTIONS_VALUE_COL_PROP) or \
                    not field.has_property(Task.EMUM_OPTIONS_LABEL_COL_PROP):
                raise ApiError.from_task("invalid_emum",
                                         "For emumerations based on an xls file, you must include 3 properties: %s, "
                                         "%s, and %s, you supplied %s" % (Task.ENUM_OPTIONS_FILE_PROP,
                                                                          Task.EMUM_OPTIONS_VALUE_COL_PROP,
                                                                          Task.EMUM_OPTIONS_LABEL_COL_PROP),
                                         task=spiff_task)

            # Get the file data from the File Service
            file_name = field.get_property(Task.ENUM_OPTIONS_FILE_PROP)
            value_column = field.get_property(Task.EMUM_OPTIONS_VALUE_COL_PROP)
            label_column = field.get_property(Task.EMUM_OPTIONS_LABEL_COL_PROP)
            data_model = FileService.get_workflow_file_data(spiff_task.workflow, file_name)
            xls = ExcelFile(data_model.data)
            df = xls.parse(xls.sheet_names[0])
            if value_column not in df:
                raise ApiError("invalid_emum",
                               "The file %s does not contain a column named % s" % (file_name, value_column))
            if label_column not in df:
                raise ApiError("invalid_emum",
                               "The file %s does not contain a column named % s" % (file_name, label_column))

            for index, row in df.iterrows():
                field.options.append({"id": row[value_column],
                                      "name": row[label_column]})
