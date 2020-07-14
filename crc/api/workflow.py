import uuid

from SpiffWorkflow.util.deep_merge import DeepMerge
from flask import g
from crc import session, app
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.api_models import WorkflowApi, WorkflowApiSchema, NavigationItem, NavigationItemSchema
from crc.models.file import FileModel, LookupDataSchema
from crc.models.stats import TaskEventModel
from crc.models.workflow import WorkflowModel, WorkflowSpecModelSchema, WorkflowSpecModel, WorkflowSpecCategoryModel, \
    WorkflowSpecCategoryModelSchema
from crc.services.file_service import FileService
from crc.services.lookup_service import LookupService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


def all_specifications():
    schema = WorkflowSpecModelSchema(many=True)
    return schema.dump(session.query(WorkflowSpecModel).all())


def add_workflow_specification(body):
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
    errors = []
    try:
        WorkflowService.test_spec(spec_id)
    except ApiError as ae:
        ae.message = "When populating all fields ... " + ae.message
        errors.append(ae)
    try:
        # Run the validation twice, the second time, just populate the required fields.
        WorkflowService.test_spec(spec_id, required_only=True)
    except ApiError as ae:
        ae.message = "When populating only required fields ... " + ae.message
        errors.append(ae)
    return ApiErrorSchema(many=True).dump(errors)


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

    # Delete all stats and workflow models related to this specification
    for workflow in session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id):
        StudyService.delete_workflow(workflow)
    session.query(WorkflowSpecModel).filter_by(id=spec_id).delete()
    session.commit()


def get_workflow(workflow_id, soft_reset=False, hard_reset=False):
    workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model, soft_reset=soft_reset, hard_reset=hard_reset)
    workflow_api_model = WorkflowService.processor_to_workflow_api(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def delete_workflow(workflow_id):
    StudyService.delete_workflow(workflow_id)


def set_current_task(workflow_id, task_id):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    spiff_task = processor.bpmn_workflow.get_task(task_id)
    _verify_user_and_role(workflow_model, spiff_task)
    user_uid = g.user.uid
    if spiff_task.state != spiff_task.COMPLETED and spiff_task.state != spiff_task.READY:
        raise ApiError("invalid_state", "You may not move the token to a task who's state is not "
                                        "currently set to COMPLETE or READY.")

    # Only reset the token if the task doesn't already have it.
    if spiff_task.state == spiff_task.COMPLETED:
        spiff_task.reset_token(reset_data=True)  # Don't try to copy the existing data back into this task.

    processor.save()
    WorkflowService.log_task_action(user_uid, workflow_model, spiff_task,
                                    WorkflowService.TASK_ACTION_TOKEN_RESET,
                                    version=processor.get_version_string())
    workflow_api_model = WorkflowService.processor_to_workflow_api(processor, spiff_task)
    return WorkflowApiSchema().dump(workflow_api_model)


def update_task(workflow_id, task_id, body, terminate_loop=None):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()

    if workflow_model is None:
        raise ApiError("invalid_workflow_id", "The given workflow id is not valid.", status_code=404)

    elif workflow_model.study is None:
        raise ApiError("invalid_study", "There is no study associated with the given workflow.", status_code=404)

    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    spiff_task = processor.bpmn_workflow.get_task(task_id)
    _verify_user_and_role(workflow_model, spiff_task)
    user_uid = g.user.uid
    if not spiff_task:
        raise ApiError("empty_task", "Processor failed to obtain task.", status_code=404)
    if spiff_task.state != spiff_task.READY:
        raise ApiError("invalid_state", "You may not update a task unless it is in the READY state. "
                                        "Consider calling a token reset to make this task Ready.")

    if terminate_loop:
        spiff_task.terminate_loop()

    spiff_task.update_data(body)
    processor.complete_task(spiff_task)
    processor.do_engine_steps()
    processor.save()

    WorkflowService.log_task_action(user_uid, workflow_model, spiff_task, WorkflowService.TASK_ACTION_COMPLETE,
                                    version=processor.get_version_string())
    workflow_api_model = WorkflowService.processor_to_workflow_api(processor)

    # If the next task

    return WorkflowApiSchema().dump(workflow_api_model)


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


def lookup(workflow_id, field_id, query=None, value=None, limit=10):
    """
    given a field in a task, attempts to find the lookup table or function associated
    with that field and runs a full-text query against it to locate the values and
    labels that would be returned to a type-ahead box.
    Tries to be fast, but first runs will be very slow.
    """
    workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
    lookup_data = LookupService.lookup(workflow, field_id, query, value, limit)
    return LookupDataSchema(many=True).dump(lookup_data)


def _verify_user_and_role(workflow_model, spiff_task):
    """Assures the currently logged in user can access the given workflow and task, or
    raises an error.
     Allow administrators to modify tasks, otherwise assure that the current user
     is allowed to edit or update the task. Will raise the appropriate error if user
     is not authorized. """

    if 'user' not in g:
        raise ApiError("logged_out", "You are no longer logged in.", status_code=401)

    if g.user.uid in app.config['ADMIN_UIDS']:
        return g.user.uid

    # If the task is in a lane, determine the user from that value.
    if spiff_task.task_spec.lane is not None:
        if spiff_task.task_spec.lane not in spiff_task.data:
            raise ApiError.from_task("invalid_role",
                                     f"This task is in a lane called '{spiff_task.task_spec.lane}', The "
                                     f" current task data must have information mapping this role to "
                                     f" a unique user id.", spiff_task)
        user_id = spiff_task.data[spiff_task.task_spec.lane]
        if g.user.uid != user_id:
            raise ApiError.from_task("role_permission",
                                     f"This task is in a lane called '{spiff_task.task_spec.lane}' which"
                                     f" must be completed by '{user_id}', but you are {g.user.uid}", spiff_task)
        return
    elif g.user.uid == workflow_model.study.user_uid:
        return

    # todo: If other users as associated with the study, and were granted access, allow them to modify tasks as well

    raise ApiError("permission_denied", "You are not authorized to edit the task data for this workflow.",
                   status_code=403, task_id=spiff_task.id, task_name=spiff_task.name, task_data=spiff_task.data)

