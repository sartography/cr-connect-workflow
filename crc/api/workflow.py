import uuid

from crc import session
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.api_models import WorkflowApi, WorkflowApiSchema
from crc.models.file import FileModel, LookupDataSchema
from crc.models.workflow import WorkflowModel, WorkflowSpecModelSchema, WorkflowSpecModel, WorkflowSpecCategoryModel, \
    WorkflowSpecCategoryModelSchema
from crc.services.file_service import FileService
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

    # Delete all stats and workflow models related to this specification
    for workflow in session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id):
        StudyService.delete_workflow(workflow)
    session.query(WorkflowSpecModel).filter_by(id=spec_id).delete()
    session.commit()


def __get_workflow_api_model(processor: WorkflowProcessor):
    spiff_tasks = processor.get_all_user_tasks()
    user_tasks = [WorkflowService.spiff_task_to_api_task(t, add_docs_and_forms=True) for t in spiff_tasks]
    workflow_api = WorkflowApi(
        id=processor.get_workflow_id(),
        status=processor.get_status(),
        last_task=WorkflowService.spiff_task_to_api_task(processor.bpmn_workflow.last_task),
        next_task=None,
        previous_task=processor.previous_task(),
        user_tasks=user_tasks,
        workflow_spec_id=processor.workflow_spec_id,
        spec_version=processor.get_spec_version(),
        is_latest_spec=processor.get_spec_version() == processor.get_latest_version_string(processor.workflow_spec_id),
        total_tasks=processor.workflow_model.total_tasks,
        completed_tasks=processor.workflow_model.completed_tasks,
        last_updated=processor.workflow_model.last_updated
    )
    next_task = processor.next_task()
    if next_task:
        workflow_api.next_task = WorkflowService.spiff_task_to_api_task(next_task, add_docs_and_forms=True)

    return workflow_api


def get_workflow(workflow_id, soft_reset=False, hard_reset=False):
    workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model, soft_reset=soft_reset, hard_reset=hard_reset)
    workflow_api_model = __get_workflow_api_model(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def delete_workflow(workflow_id):
    StudyService.delete_workflow(workflow_id)

def set_current_task(workflow_id, task_id):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    task = processor.bpmn_workflow.get_task(task_id)
    if task.state != task.COMPLETED:
        raise ApiError("invalid_state", "You may not move the token to a task who's state is not "
                                        "currently set to COMPLETE.")

    task.reset_token(reset_data=False)  # we could optionally clear the previous data.
    processor.save()
    WorkflowService.log_task_action(processor, task, WorkflowService.TASK_ACTION_TOKEN_RESET)
    workflow_api_model = __get_workflow_api_model(processor)
    return WorkflowApiSchema().dump(workflow_api_model)


def update_task(workflow_id, task_id, body):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    task = processor.bpmn_workflow.get_task(task_id)
    if task.state != task.READY:
        raise ApiError("invalid_state", "You may not update a task unless it is in the READY state. "
                                        "Consider calling a token reset to make this task Ready.")
    task.update_data(body)
    processor.complete_task(task)
    processor.do_engine_steps()
    processor.save()
    WorkflowService.log_task_action(processor, task, WorkflowService.TASK_ACTION_COMPLETE)

    workflow_api_model = __get_workflow_api_model(processor)
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


def lookup(workflow_id, task_id, field_id, query, limit):
    """
    given a field in a task, attempts to find the lookup table associated with that field
    and runs a full-text query against it to locate the values and labels that would be
    returned to a type-ahead box.
    """
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    if not workflow_model:
        raise ApiError("unknown_workflow", "No workflow found with id: %i" % workflow_id)
    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    spiff_task = processor.bpmn_workflow.get_task(task_id)
    if not spiff_task:
        raise ApiError("unknown_task", "No task with %s found in workflow: %i" % (task_id, workflow_id))
    field = None
    for f in spiff_task.task_spec.form.fields:
        if f.id == field_id:
            field = f
    if not field:
        raise ApiError("unknown_field", "No field named %s in task %s" % (task_id, spiff_task.task_spec.name))

    lookup_table = WorkflowService.get_lookup_table(spiff_task, field)
    lookup_data = WorkflowService.run_lookup_query(lookup_table, query, limit)
    return LookupDataSchema(many=True).dump(lookup_data)