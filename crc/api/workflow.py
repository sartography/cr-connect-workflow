import uuid

from flask import g

from crc import session
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.api_models import WorkflowApiSchema
from crc.models.file import FileModel, LookupDataSchema
from crc.models.study import StudyModel, WorkflowMetadata
from crc.models.task_event import TaskEventModel, TaskEvent, TaskEventSchema
from crc.models.user import UserModelSchema
from crc.models.workflow import WorkflowModel, WorkflowSpecModelSchema, WorkflowSpecModel, WorkflowSpecCategoryModel, \
    WorkflowSpecCategoryModelSchema
from crc.services.error_service import ValidationErrorService
from crc.services.file_service import FileService
from crc.services.lookup_service import LookupService
from crc.services.study_service import StudyService
from crc.services.user_service import UserService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


def all_specifications():
    schema = WorkflowSpecModelSchema(many=True)
    return schema.dump(session.query(WorkflowSpecModel).all())


def add_workflow_specification(body):
    count = session.query(WorkflowSpecModel).filter_by(category_id=body['category_id']).count()
    body['display_order'] = count
    new_spec: WorkflowSpecModel = WorkflowSpecModelSchema().load(body, session=session)
    session.add(new_spec)
    session.commit()
    return WorkflowSpecModelSchema().dump(new_spec)


def get_workflow_specification(spec_id):
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')

    spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        raise ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')

    return WorkflowSpecModelSchema().dump(spec)


def validate_workflow_specification(spec_id):
    errors = {}
    try:
        WorkflowService.test_spec(spec_id)
    except ApiError as ae:
        ae.message = "When populating all fields ... \n" + ae.message
        errors['all'] = ae
    try:
        # Run the validation twice, the second time, just populate the required fields.
        WorkflowService.test_spec(spec_id, required_only=True)
    except ApiError as ae:
        ae.message = "When populating only required fields ... \n" + ae.message
        errors['required'] = ae
    interpreted_errors = ValidationErrorService.interpret_validation_errors(errors)
    return ApiErrorSchema(many=True).dump(interpreted_errors)


def update_workflow_specification(spec_id, body):
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Spec ID.')
    spec = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        raise ApiError('unknown_study', 'The spec "' + spec_id + '" is not recognized.')

    schema = WorkflowSpecModelSchema()
    spec = schema.load(body, session=session, instance=spec, partial=True)
    session.add(spec)
    session.commit()
    return schema.dump(spec)


def delete_workflow_specification(spec_id):
    if spec_id is None:
        raise ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')

    spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        raise ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')

    # Delete all items in the database related to the deleted workflow spec.
    files = session.query(FileModel).filter_by(workflow_spec_id=spec_id).all()
    for file in files:
        FileService.delete_file(file.id)

    session.query(TaskEventModel).filter(TaskEventModel.workflow_spec_id == spec_id).delete()

    # Delete all events and workflow models related to this specification
    for workflow in session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id):
        StudyService.delete_workflow(workflow.id)
    session.query(WorkflowSpecModel).filter_by(id=spec_id).delete()
    session.commit()


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


def restart_workflow(workflow_id, clear_data=False):
    """Restart a workflow with the latest spec.
       Clear data allows user to restart the workflow without previous data."""
    workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    WorkflowProcessor.reset(workflow_model, clear_data=clear_data)
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
        workflow_meta = WorkflowMetadata.from_workflow(workflow)
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
        spiff_task.reset_token(reset_data=True)  # Don't try to copy the existing data back into this task.

    processor.save()
    WorkflowService.log_task_action(user_uid, processor, spiff_task, WorkflowService.TASK_ACTION_TOKEN_RESET)
    WorkflowService.update_task_assignments(processor)

    workflow_api_model = WorkflowService.processor_to_workflow_api(processor, spiff_task)
    return WorkflowApiSchema().dump(workflow_api_model)


def update_task(workflow_id, task_id, body, terminate_loop=None, update_all=False):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    if workflow_model is None:
        raise ApiError("invalid_workflow_id", "The given workflow id is not valid.", status_code=404)

    elif workflow_model.study is None:
        raise ApiError("invalid_study", "There is no study associated with the given workflow.", status_code=404)

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

    if terminate_loop:
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
    processor.complete_task(task)
    processor.do_engine_steps()
    processor.save()
    WorkflowService.log_task_action(user.uid, processor, task, WorkflowService.TASK_ACTION_COMPLETE)


def list_workflow_spec_categories():
    schema = WorkflowSpecCategoryModelSchema(many=True)
    return schema.dump(session.query(WorkflowSpecCategoryModel).all())


def get_workflow_spec_category(cat_id):
    schema = WorkflowSpecCategoryModelSchema()
    return schema.dump(session.query(WorkflowSpecCategoryModel).filter_by(id=cat_id).first())


def add_workflow_spec_category(body):
    schema = WorkflowSpecCategoryModelSchema()
    new_cat: WorkflowSpecCategoryModel = schema.load(body, session=session)
    session.add(new_cat)
    session.commit()
    return schema.dump(new_cat)


def update_workflow_spec_category(cat_id, body):
    if cat_id is None:
        raise ApiError('unknown_category', 'Please provide a valid Workflow Spec Category ID.')

    category = session.query(WorkflowSpecCategoryModel).filter_by(id=cat_id).first()

    if category is None:
        raise ApiError('unknown_category', 'The category "' + cat_id + '" is not recognized.')

    schema = WorkflowSpecCategoryModelSchema()
    category = schema.load(body, session=session, instance=category, partial=True)
    session.add(category)
    session.commit()
    return schema.dump(category)


def delete_workflow_spec_category(cat_id):
    session.query(WorkflowSpecCategoryModel).filter_by(id=cat_id).delete()
    session.commit()


def lookup(workflow_id, task_spec_name, field_id, query=None, value=None, limit=10):
    """
    given a field in a task, attempts to find the lookup table or function associated
    with that field and runs a full-text query against it to locate the values and
    labels that would be returned to a type-ahead box.
    Tries to be fast, but first runs will be very slow.
    """
    workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
    lookup_data = LookupService.lookup(workflow, task_spec_name, field_id, query, value, limit)
    return LookupDataSchema(many=True).dump(lookup_data)


def _verify_user_and_role(processor, spiff_task):
    """Assures the currently logged in user can access the given workflow and task, or
    raises an error.  """

    user = UserService.current_user(allow_admin_impersonate=True)
    allowed_users = WorkflowService.get_users_assigned_to_task(processor, spiff_task)
    if user.uid not in allowed_users:
        raise ApiError.from_task("permission_denied",
                                 f"This task must be completed by '{allowed_users}', "
                                 f"but you are {user.uid}", spiff_task)
