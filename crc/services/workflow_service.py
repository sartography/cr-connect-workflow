from datetime import datetime

from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.dmn.specs.BusinessRuleTask import BusinessRuleTask
from SpiffWorkflow.specs import CancelTask, StartTask
from flask import g
from pandas import ExcelFile
from sqlalchemy import func

from crc import db
from crc.api.common import ApiError
from crc.models.api_models import Task, MultiInstanceType
import jinja2
from jinja2 import Template

from crc.models.file import FileDataModel, LookupFileModel, LookupDataModel
from crc.models.stats import TaskEventModel
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor, CustomBpmnScriptEngine
from SpiffWorkflow import Task as SpiffTask, WorkflowException


class WorkflowService(object):

    TASK_ACTION_COMPLETE = "Complete"
    TASK_ACTION_TOKEN_RESET = "Backwards Move"
    TASK_ACTION_HARD_RESET = "Restart (Hard)"
    TASK_ACTION_SOFT_RESET = "Restart (Soft)"

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
        version = WorkflowProcessor.get_latest_version_string(spec_id)
        spec = WorkflowProcessor.get_spec(spec_id, version)
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
                        task, add_docs_and_forms=True)  # Assure we try to process the documenation, and raise those errors.
                    WorkflowProcessor.populate_form_with_random_data(task, task_api)
                    task.complete()
            except WorkflowException as we:
                raise ApiError.from_task_spec("workflow_execution_exception", str(we),
                                              we.sender)

    @staticmethod
    def spiff_task_to_api_task(spiff_task, add_docs_and_forms=False):
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

        props = []
        if hasattr(spiff_task.task_spec, 'extensions'):
            for id, val in spiff_task.task_spec.extensions.items():
                props.append({"id": id, "value": val})

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
                    info["mi_index"],
                    process_name=spiff_task.task_spec._wf_spec.description,
                    properties=props)

        # Only process the form and documentation if requested.
        # The task should be in a completed or a ready state, and should
        # not be a previously completed MI Task.
        if add_docs_and_forms:
            if hasattr(spiff_task.task_spec, "form"):
                task.form = spiff_task.task_spec.form
                for field in task.form.fields:
                    WorkflowService.process_options(spiff_task, field)

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

#            return "Error processing template. %s" % ue.message
            raise ApiError(code="template_error", message="Error processing template for task %s: %s" %
                                                          (spiff_task.task_spec.name, str(ue)), status_code=500)
        # TODO:  Catch additional errors and report back.

    @staticmethod
    def process_options(spiff_task, field):
        lookup_model = WorkflowService.get_lookup_table(spiff_task, field)

        # If lookup is set to true, do not populate options, a lookup will happen later.
        if field.has_property(Task.EMUM_OPTIONS_AS_LOOKUP) and field.get_property(Task.EMUM_OPTIONS_AS_LOOKUP):
            pass
        else:
            data = db.session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_model).all()
            if not hasattr(field, 'options'):
                field.options = []
            for d in data:
                field.options.append({"id": d.value, "name": d.label})

    @staticmethod
    def get_lookup_table(spiff_task, field):
        """ Checks to see if the options are provided in a separate lookup table associated with the
        workflow, and if so, assures that data exists in the database, and return a model than can be used
        to locate that data. """
        if field.has_property(Task.ENUM_OPTIONS_FILE_PROP):
            if not field.has_property(Task.EMUM_OPTIONS_VALUE_COL_PROP) or \
                    not field.has_property(Task.EMUM_OPTIONS_LABEL_COL_PROP):
                raise ApiError.from_task("invalid_emum",
                                         "For enumerations based on an xls file, you must include 3 properties: %s, "
                                         "%s, and %s" % (Task.ENUM_OPTIONS_FILE_PROP,
                                                         Task.EMUM_OPTIONS_VALUE_COL_PROP,
                                                         Task.EMUM_OPTIONS_LABEL_COL_PROP),
                                         task=spiff_task)

            # Get the file data from the File Service
            file_name = field.get_property(Task.ENUM_OPTIONS_FILE_PROP)
            value_column = field.get_property(Task.EMUM_OPTIONS_VALUE_COL_PROP)
            label_column = field.get_property(Task.EMUM_OPTIONS_LABEL_COL_PROP)
            data_model = FileService.get_workflow_file_data(spiff_task.workflow, file_name)
            lookup_model = WorkflowService._get_lookup_table_from_data_model(data_model, value_column, label_column)
            return lookup_model

    @staticmethod
    def _get_lookup_table_from_data_model(data_model: FileDataModel, value_column, label_column):
        """ In some cases the lookup table can be very large.  This method will add all values to the database
         in a way that can be searched and returned via an api call - rather than sending the full set of
          options along with the form.  It will only open the file and process the options if something has
          changed.  """

        lookup_model = db.session.query(LookupFileModel) \
            .filter(LookupFileModel.file_data_model_id == data_model.id) \
            .filter(LookupFileModel.value_column == value_column) \
            .filter(LookupFileModel.label_column == label_column).first()

        if not lookup_model:
            xls = ExcelFile(data_model.data)
            df = xls.parse(xls.sheet_names[0])  # Currently we only look at the fist sheet.
            if value_column not in df:
                raise ApiError("invalid_emum",
                               "The file %s does not contain a column named % s" % (data_model.file_model.name,
                                                                                    value_column))
            if label_column not in df:
                raise ApiError("invalid_emum",
                               "The file %s does not contain a column named % s" % (data_model.file_model.name,
                                                                                    label_column))

            lookup_model = LookupFileModel(label_column=label_column, value_column=value_column,
                                           file_data_model_id=data_model.id)

            db.session.add(lookup_model)
            for index, row in df.iterrows():
                lookup_data = LookupDataModel(lookup_file_model=lookup_model,
                                              value=row[value_column],
                                              label=row[label_column],
                                              data=row.to_json())
                db.session.add(lookup_data)
            db.session.commit()

        return lookup_model

    @staticmethod
    def run_lookup_query(lookupFileModel, query, limit):
        db_query = LookupDataModel.query.filter(LookupDataModel.lookup_file_model == lookupFileModel)

        query = query.strip()
        if len(query) > 1:
            if ' ' in query:
                terms = query.split(' ')
                query = ""
                new_terms = []
                for t in terms:
                    new_terms.append(t + ":*")
                query = '|'.join(new_terms)
            else:
                query = "%s:*" % query
            db_query = db_query.filter(LookupDataModel.label.match(query))

        #            db_query = db_query.filter(text("lookup_data.label @@ to_tsquery('simple', '%s')" % query))

        return db_query.limit(limit).all()

    @staticmethod
    def log_task_action(processor, spiff_task, action):
        task = WorkflowService.spiff_task_to_api_task(spiff_task)
        workflow_model = processor.workflow_model
        task_event = TaskEventModel(
            study_id=workflow_model.study_id,
            user_uid=g.user.uid,
            workflow_id=workflow_model.id,
            workflow_spec_id=workflow_model.workflow_spec_id,
            spec_version=workflow_model.spec_version,
            action=action,
            task_id=task.id,
            task_name=task.name,
            task_title=task.title,
            task_type=str(task.type),
            task_state=task.state,
            mi_type=task.mi_type.value,  # Some tasks have a repeat behavior.
            mi_count=task.mi_count,  # This is the number of times the task could repeat.
            mi_index=task.mi_index,  # And the index of the currently repeating task.
            process_name=task.process_name,
            date=datetime.now(),
        )
        db.session.add(task_event)
        db.session.commit()



