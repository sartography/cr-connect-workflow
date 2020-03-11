import uuid

from crc.api.stats import update_workflow_stats, log_task_complete
from crc import session, auth
from crc.api.common import ApiError, ApiErrorSchema
from crc.api.file import delete_file
from crc.models.api_models import Task, WorkflowApi, WorkflowApiSchema
from crc.models.file import FileModel
from crc.models.workflow import WorkflowModel, WorkflowSpecModelSchema, WorkflowSpecModel
from crc.services.workflow_processor import WorkflowProcessor


def all_specifications():
    schema = WorkflowSpecModelSchema(many=True)
    return schema.dump(session.query(WorkflowSpecModel).all())


@auth.login_required
def add_workflow_specification(body):
    new_spec = WorkflowSpecModelSchema().load(body, session=session)
    session.add(new_spec)
    session.commit()
    return WorkflowSpecModelSchema().dump(new_spec)


@auth.login_required
def get_workflow_specification(spec_id):
    if spec_id is None:
        error = ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')
        return ApiErrorSchema.dump(error), 404

    spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        error = ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404

    return WorkflowSpecModelSchema().dump(spec)


@auth.login_required
def update_workflow_specification(spec_id, body):
    spec = WorkflowSpecModelSchema().load(body, session=session)
    spec.id = spec_id
    session.add(spec)
    session.commit()
    return WorkflowSpecModelSchema().dump(spec)


@auth.login_required
def delete_workflow_specification(spec_id):
    if spec_id is None:
        error = ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')
        return ApiErrorSchema.dump(error), 404

    spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        error = ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404

    # Delete all items in the database related to the deleted workflow spec.
    files = session.query(FileModel).filter_by(workflow_spec_id=spec_id).all()
    for file in files:
        delete_file(file.id)

    session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).delete()
    session.query(WorkflowSpecModel).filter_by(id=spec_id).delete()
    session.commit()


def __get_workflow_api_model(processor: WorkflowProcessor):
    spiff_tasks = processor.get_all_user_tasks()
    user_tasks = list(map(Task.from_spiff, spiff_tasks))
    workflow_api = WorkflowApi(
        id=processor.get_workflow_id(),
        status=processor.get_status(),
        last_task=Task.from_spiff(processor.bpmn_workflow.last_task),
        next_task=None,
        user_tasks=user_tasks,
        workflow_spec_id=processor.workflow_spec_id,
        spec_version=processor.get_spec_version(),
        is_latest_spec=processor.get_spec_version() == processor.get_latest_version_string(processor.workflow_spec_id)
    )
    if processor.next_task():
        workflow_api.next_task = Task.from_spiff(processor.next_task())
    return workflow_api


@auth.login_required
def get_workflow(workflow_id, soft_reset=False, hard_reset=False):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model, soft_reset=soft_reset, hard_reset=hard_reset)

    workflow_api_model = __get_workflow_api_model(processor)
    update_workflow_stats(workflow_model, workflow_api_model)
    return WorkflowApiSchema().dump(workflow_api_model)


@auth.login_required
def delete(workflow_id):
    session.query(WorkflowModel).filter_by(id=workflow_id).delete()
    session.commit()


@auth.login_required
def get_task(workflow_id, task_id):
    workflow = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    return workflow.bpmn_workflow().get_task(task_id)


@auth.login_required
def update_task(workflow_id, task_id, body):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model)
    task_id = uuid.UUID(task_id)
    task = processor.bpmn_workflow.get_task(task_id)
    task.data = body
    processor.complete_task(task)
    processor.do_engine_steps()
    workflow_model.last_completed_task_id = task.id
    workflow_model.bpmn_workflow_json = processor.serialize()
    session.add(workflow_model)
    session.commit()

    workflow_api_model = __get_workflow_api_model(processor)
    update_workflow_stats(workflow_model, workflow_api_model)
    log_task_complete(workflow_model, task_id)
    return WorkflowApiSchema().dump(workflow_api_model)
