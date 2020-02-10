import uuid

from crc.api.file import delete_file
from crc import session
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.workflow import WorkflowModel, WorkflowSpecModelSchema, WorkflowSpecModel, \
    Task, WorkflowApiSchema, WorkflowApi
from crc.services.workflow_processor import WorkflowProcessor
from crc.models.file import FileModel


def all_specifications():
    schema = WorkflowSpecModelSchema(many=True)
    return schema.dump(session.query(WorkflowSpecModel).all())


def add_workflow_specification(body):
    new_spec = WorkflowSpecModelSchema().load(body, session=session)
    session.add(new_spec)
    session.commit()
    return WorkflowSpecModelSchema().dump(new_spec)


def get_workflow_specification(spec_id):
    if spec_id is None:
        error = ApiError('unknown_spec', 'Please provide a valid Workflow Specification ID.')
        return ApiErrorSchema.dump(error), 404

    spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()

    if spec is None:
        error = ApiError('unknown_spec', 'The Workflow Specification "' + spec_id + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404

    return WorkflowSpecModelSchema().dump(spec)


def update_workflow_specification(spec_id, body):
    spec = WorkflowSpecModelSchema().load(body, session=session)
    spec.id = spec_id
    session.add(spec)
    session.commit()
    return WorkflowSpecModelSchema().dump(spec)


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
    user_tasks = map(Task.from_spiff, spiff_tasks)
    workflow_api = WorkflowApi(
        id=processor.get_workflow_id(),
        status=processor.get_status(),
        last_task=Task.from_spiff(processor.bpmn_workflow.last_task),
        next_task=None,
        user_tasks=user_tasks,
        workflow_spec_id=processor.workflow_spec_id
    )
    if(processor.next_task()):
        workflow_api.next_task = Task.from_spiff(processor.next_task()),
    return workflow_api

def get_workflow(workflow_id):
    schema = WorkflowApiSchema()
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model.workflow_spec_id,
                                  workflow_model.bpmn_workflow_json)
    return schema.dump(__get_workflow_api_model(processor))


def delete(workflow_id):
    session.query(WorkflowModel).filter_by(id=workflow_id).delete()
    session.commit()

def get_task(workflow_id, task_id):
    workflow = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    return workflow.bpmn_workflow().get_task(task_id)


def update_task(workflow_id, task_id, body):
    workflow_model = session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow_model.workflow_spec_id, workflow_model.bpmn_workflow_json)
    task_id = uuid.UUID(task_id)
    task = processor.bpmn_workflow.get_task(task_id)
    task.data = body
    processor.complete_task(task)
    processor.do_engine_steps()
    workflow_model.last_completed_task_id = task.id
    workflow_model.bpmn_workflow_json = processor.serialize()
    session.add(workflow_model)
    session.commit()
    return WorkflowApiSchema().dump(__get_workflow_api_model(processor)
                                    )
