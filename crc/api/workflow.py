import uuid

from flask import g

from crc import session
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.api_models import WorkflowApiSchema
from crc.models.study import StudyModel, WorkflowMetadata, StudyStatus
from crc.models.task_event import TaskEventModel, TaskEvent, TaskEventSchema
from crc.models.task_log import TaskLogModelSchema, TaskLogQuery, TaskLogQuerySchema
from crc.models.workflow import WorkflowModel, WorkflowSpecInfoSchema, WorkflowSpecCategorySchema
from crc.services.error_service import ValidationErrorService
from crc.services.lookup_service import LookupService
from crc.services.spec_file_service import SpecFileService
from crc.services.study_service import StudyService
from crc.services.task_logging_service import TaskLoggingService
from crc.services.user_service import UserService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from crc.services.workflow_spec_service import WorkflowSpecService


def all_specifications(libraries=False,standalone=False):
    spec_service = WorkflowSpecService()
    if libraries and standalone:
        raise ApiError('inconceivable!', 'You should specify libraries or standalone, but not both')

    if libraries:
        workflows = spec_service.get_libraries()
        return WorkflowSpecInfoSchema(many=True).dump(workflows)

    if standalone:
        workflows = spec_service.get_standalones()
        return WorkflowSpecInfoSchema(many=True).dump(workflows)

    # return standard workflows (not library, not standalone)
    specs = spec_service.get_specs()
    return WorkflowSpecInfoSchema(many=True).dump(specs)


def add_workflow_specification(body):
    spec = WorkflowSpecInfoSchema().load(body)
    spec_service = WorkflowSpecService()
    category = spec_service.get_category(spec.category_id)
    spec.category = category
    workflows = spec_service.cleanup_workflow_spec_display_order(category)
    size = len(workflows)
    spec.display_order = size
    spec_service.add_spec(spec)
    return WorkflowSpecInfoSchema().dump(spec)


def get_workflow_specification(spec_id):
    spec_service = WorkflowSpecService()
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')
    spec = spec_service.get_spec(spec_id)

    if spec is None:
        raise ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')

    return WorkflowSpecInfoSchema().dump(spec)

def validate_spec_and_library(spec_id,library_id):
    spec_service = WorkflowSpecService()

    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')
    if library_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Library Specification ID.')

    spec = spec_service.get_spec(spec_id)
    library = spec_service.get_spec(library_id);
    if spec is None:
        raise ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')
    if library is None:
        raise ApiError('unknown_spec', 'The Library Specification "' + library_id + '" is not recognized.')
    if not library.library:
        raise ApiError('unknown_spec', 'Linked workflow spec is not a library.')


def add_workflow_spec_library(spec_id, library_id):
    validate_spec_and_library(spec_id, library_id)
    spec_service = WorkflowSpecService()
    spec = spec_service.get_spec(spec_id)
    if library_id in spec.libraries:
        raise ApiError('invalid_request', 'The Library Specification "' + library_id + '" is already attached.')

    spec.libraries.append(library_id)
    spec_service.update_spec(spec)
    return WorkflowSpecInfoSchema().dump(spec)


def drop_workflow_spec_library(spec_id, library_id):
    validate_spec_and_library(spec_id, library_id)
    spec_service = WorkflowSpecService()

    spec = spec_service.get_spec(spec_id)

    if library_id in spec.libraries:
        spec.libraries.remove(library_id)
    spec_service.update_spec(spec)
    return WorkflowSpecInfoSchema().dump(spec)


def validate_workflow_specification(spec_id, study_id=None, test_until=None):
    try:
        master_spec = WorkflowSpecService().master_spec
        if study_id is not None:
            study_model = session.query(StudyModel).filter(StudyModel.id == study_id).first()
            statuses = WorkflowProcessor.run_master_spec(master_spec, study_model)
            if spec_id in statuses and statuses[spec_id]['status'] == 'disabled':
                raise ApiError(code='disabled_workflow',
                               message=f"This workflow is disabled. {statuses[spec_id]['message']}")
        WorkflowService.test_spec(spec_id, study_id, test_until)
        WorkflowService.test_spec(spec_id, study_id, test_until, required_only=True)
    except ApiError as ae:
        error = ae
        error = ValidationErrorService.interpret_validation_error(error)
        return ApiErrorSchema(many=True).dump([error])
    return []


def update_workflow_specification(spec_id, body):
    spec_service = WorkflowSpecService()

    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Spec ID.')
    spec = spec_service.get_spec(spec_id)

    if spec is None:
        raise ApiError('unknown_study', 'The spec "' + spec_id + '" is not recognized.')

    # Make sure they don't try to change the display_order
    # There is a separate endpoint for this
    body['display_order'] = spec.display_order

    # Libraries and standalone workflows don't get a category_id
    if body['library'] is True or body['standalone'] is True:
        body['category_id'] = None
    spec = WorkflowSpecInfoSchema().load(body)
    spec_service.update_spec(spec)
    return WorkflowSpecInfoSchema().dump(spec)


def delete_workflow_specification(spec_id):
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')
    spec_service = WorkflowSpecService()
    spec = spec_service.get_spec(spec_id)
    if spec is None:
        raise ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')
    spec_service.delete_spec(spec_id)
    spec_service.cleanup_workflow_spec_display_order(spec.category_id)


def reorder_workflow_specification(spec_id, direction):
    if direction not in ('up', 'down'):
        raise ApiError(code='bad_direction',
                       message='The direction must be `up` or `down`.')
    spec_service = WorkflowSpecService()

    spec = spec_service.get_spec(spec_id)
    if spec:
        ordered_specs = spec_service.reorder_spec(spec, direction)
    else:
        raise ApiError(code='bad_spec_id',
                       message=f'The spec_id {spec_id} did not return a specification. Please check that it is valid.')
    return WorkflowSpecInfoSchema(many=True).dump(ordered_specs)


def get_workflow_from_spec(spec_id):
    workflow_model = WorkflowService.get_workflow_from_spec(spec_id, g.user)
    processor = WorkflowProcessor(workflow_model)

    processor.do_engine_steps()
    processor.save()
    WorkflowService.update_task_assignments(processor)

    workflow_api_model = WorkflowService.processor_to_workflow_api(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def get_workflow(workflow_id, do_engine_steps=True):
    """Retrieve workflow based on workflow_id, and return it in the last saved State.
       If do_engine_steps is False, return the workflow without running any engine tasks or logging any events. """
    workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model)

    if do_engine_steps:
        processor.do_engine_steps()
        processor.save()
        WorkflowService.update_task_assignments(processor)

    workflow_api_model = WorkflowService.processor_to_workflow_api(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def restart_workflow(workflow_id, clear_data=False, delete_files=False):
    """Restart a workflow with the latest spec.
       Clear data allows user to restart the workflow without previous data."""
    workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    WorkflowProcessor.reset(workflow_model, clear_data=clear_data, delete_files=delete_files)
    return get_workflow(workflow_model.id)


def get_task_events(action = None, workflow = None, study = None):
    """Provides a way to see a history of what has happened, or get a list of tasks that need your attention."""
    user = UserService.current_user(allow_admin_impersonate=True)
    studies = session.query(StudyModel).filter(StudyModel.user_uid==user.uid)
    studyids = [s.id for s in studies]
    query = session.query(TaskEventModel).filter((TaskEventModel.study_id.in_(studyids)) | \
                                                 (TaskEventModel.user_uid==user.uid))
    if action:
        query = query.filter(TaskEventModel.action == action)
    if workflow:
        query = query.filter(TaskEventModel.workflow_id == workflow)
    if study:
        query = query.filter(TaskEventModel.study_id == study)
    events = query.all()

    # Turn the database records into something a little richer for the UI to use.
    task_events = []
    for event in events:
        study = session.query(StudyModel).filter(StudyModel.id == event.study_id).first()
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == event.workflow_id).first()
        spec = WorkflowSpecService().get_spec(workflow.workflow_spec_id)
        workflow_meta = WorkflowMetadata.from_workflow(workflow, spec)
        if study and study.status in [StudyStatus.open_for_enrollment, StudyStatus.in_progress]:
            task_events.append(TaskEvent(event, study, workflow_meta))
    return TaskEventSchema(many=True).dump(task_events)


def delete_workflow(workflow_id):
    StudyService.delete_workflow(workflow_id)


def set_current_task(workflow_id, task_id):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    spiff_task = processor.bpmn_workflow.get_task(task_id)
    _verify_user_and_role(processor, spiff_task)
    user_uid = UserService.current_user(allow_admin_impersonate=True).uid
    if spiff_task.state != spiff_task.COMPLETED and spiff_task.state != spiff_task.READY:
        raise ApiError("invalid_state", "You may not move the token to a task who's state is not "
                                        "currently set to COMPLETE or READY.")

    # If we have an interrupt task, run it.
    processor.cancel_notify()

    # Only reset the token if the task doesn't already have it.
    if spiff_task.state == spiff_task.COMPLETED:
        spiff_task.reset_token({}, reset_data=True)  # Don't try to copy the existing data back into this task.

    processor.save()
    WorkflowService.log_task_action(user_uid, processor, spiff_task, WorkflowService.TASK_ACTION_TOKEN_RESET)
    WorkflowService.update_task_assignments(processor)

    workflow_api_model = WorkflowService.processor_to_workflow_api(processor, spiff_task)
    return WorkflowApiSchema().dump(workflow_api_model)


def update_task(workflow_id, task_id, body, terminate_loop=None, update_all=False):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    if workflow_model is None:
        raise ApiError("invalid_workflow_id", "The given workflow id is not valid.", status_code=404)

    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    spiff_task = processor.bpmn_workflow.get_task(task_id)
    _verify_user_and_role(processor, spiff_task)
    user = UserService.current_user(allow_admin_impersonate=False) # Always log as the real user.

    if not spiff_task:
        raise ApiError("empty_task", "Processor failed to obtain task.", status_code=404)
    if spiff_task.state != spiff_task.READY:
        raise ApiError("invalid_state", "You may not update a task unless it is in the READY state. "
                                        "Consider calling a token reset to make this task Ready.")

    if terminate_loop and spiff_task.is_looping():
        spiff_task.terminate_loop()

    # Extract the details specific to the form submitted
    form_data = WorkflowService().extract_form_data(body, spiff_task)

    # Update the task
    __update_task(processor, spiff_task, form_data, user)

    # If we need to update all tasks, then get the next ready task and if it a multi-instance with the same
    # task spec, complete that form as well.
    if update_all:
        last_index = spiff_task.task_info()["mi_index"]
        next_task = processor.next_task()
        while next_task and next_task.task_info()["mi_index"] > last_index:
            __update_task(processor, next_task, form_data, user)
            last_index = next_task.task_info()["mi_index"]
            next_task = processor.next_task()

    WorkflowService.update_task_assignments(processor)
    workflow_api_model = WorkflowService.processor_to_workflow_api(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def __update_task(processor, task, data, user):
    """All the things that need to happen when we complete a form, abstracted
    here because we need to do it multiple times when completing all tasks in
    a multi-instance task"""
    task.update_data(data)
    WorkflowService.post_process_form(task)  # some properties may update the data store.
    processor.complete_task(task)
    # Log the action before doing the engine steps, as doing so could effect the state of the task
    # the workflow could wrap around in the ngine steps, and the task could jump from being completed to
    # another state.  What we are logging here is the completion.
    WorkflowService.log_task_action(user.uid, processor, task, WorkflowService.TASK_ACTION_COMPLETE)
    processor.do_engine_steps()
    processor.save()


def list_workflow_spec_categories():
    spec_service = WorkflowSpecService()
    categories = spec_service.get_categories()
    return WorkflowSpecCategorySchema(many=True).dump(categories)



def get_workflow_spec_category(cat_id):
    spec_service = WorkflowSpecService()
    category = spec_service.get_category(cat_id)
    return WorkflowSpecCategorySchema().dump(category)


def add_workflow_spec_category(body):
    spec_service = WorkflowSpecService()
    category = WorkflowSpecCategorySchema().load(body)
    spec_service.add_category(category)
    return WorkflowSpecCategorySchema().dump(category)

def update_workflow_spec_category(cat_id, body):
    if cat_id is None:
        raise ApiError('unknown_category', 'Please provide a valid Workflow Spec Category ID.')
    spec_service = WorkflowSpecService()
    category = spec_service.get_category(cat_id)
    if category is None:
        raise ApiError('unknown_category', 'The category "' + cat_id + '" is not recognized.')

    # Make sure they don't try to change the display_order
    # There is a separate endpoint for that
    body['display_order'] = category.display_order
    category = WorkflowSpecCategorySchema().load(body)
    spec_service.update_category(category)
    return WorkflowSpecCategorySchema().dump(category)


def delete_workflow_spec_category(cat_id):
    spec_service = WorkflowSpecService()
    spec_service.delete_category(cat_id)


def reorder_workflow_spec_category(cat_id, direction):
    if direction not in ('up', 'down'):
        raise ApiError(code='bad_direction',
                       message='The direction must be `up` or `down`.')
    spec_service = WorkflowSpecService()
    spec_service.cleanup_category_display_order()
    category = spec_service.get_category(cat_id)
    if category:
        ordered_categories = spec_service.reorder_workflow_spec_category(category, direction)
        return WorkflowSpecCategorySchema(many=True).dump(ordered_categories)
    else:
        raise ApiError(code='bad_category_id',
                       message=f'The category id {cat_id} did not return a Workflow Spec Category. Make sure it is a valid ID.')


def lookup(workflow_id, task_spec_name, field_id, query=None, value=None, limit=10):
    """
    given a field in a task, attempts to find the lookup table or function associated
    with that field and runs a full-text query against it to locate the values and
    labels that would be returned to a type-ahead box.
    Tries to be fast, but first runs will be very slow.
    """
    workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
    lookup_data = LookupService.lookup(workflow, task_spec_name, field_id, query, value, limit)
    # Just return the data
    return lookup_data


def lookup_ldap(query=None, limit=10):
    """
    perform a lookup against the LDAP server without needing a provided workflow.
    """
    value = None
    lookup_data = LookupService._run_ldap_query(query, value, limit)
    return lookup_data


def _verify_user_and_role(processor, spiff_task):
    """Assures the currently logged in user can access the given workflow and task, or
    raises an error.  """

    user = UserService.current_user(allow_admin_impersonate=True)
    allowed_users = WorkflowService.get_users_assigned_to_task(processor, spiff_task)
    if user.uid not in allowed_users:
        raise ApiError.from_task("permission_denied",
                                 f"This task must be completed by '{allowed_users}', "
                                 f"but you are {user.uid}", spiff_task)


def get_logs_for_workflow(workflow_id, body):
    task_log_query = TaskLogQuery(**body)
    return TaskLogQuerySchema().dump(
        TaskLoggingService.get_logs_for_workflow(workflow_id, task_log_query))
