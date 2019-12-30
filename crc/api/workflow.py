from crc import db
from crc.models import WorkflowModel, WorkflowSchema, WorkflowSpecSchema, WorkflowSpecModel, \
    Task, TaskSchema
from crc.workflow_processor import WorkflowProcessor


def all_specifications():
    schema = WorkflowSpecSchema(many=True)
    return schema.dump(db.session.query(WorkflowSpecModel).all())


def get_workflow(workflow_id):
    schema = WorkflowSchema()
    workflow = db.session.query(WorkflowModel).filter_by(id=workflow_id).first()
    return schema.dump(workflow)


def get_tasks(workflow_id):
    workflow = db.session.query(WorkflowModel).filter_by(id=workflow_id).first()
    processor = WorkflowProcessor(workflow.workflow_spec_id, workflow.bpmn_workflow_json)
    spiff_tasks = processor.get_ready_user_tasks()
    tasks = []
    for st in spiff_tasks:
        tasks.append(Task.from_spiff(st))
    return TaskSchema(many=True).dump(tasks)


def get_task(workflow_id, task_id):
    workflow = db.session.query(WorkflowModel).filter_by(id=workflow_id).first()
    return workflow.bpmn_workflow().get_task(task_id)


def update_task(workflow_id, task_id, body):
    global bpmn_workflow
    for field in body["task"]["form"]:
        print("Setting " + field["id"] + " to " + field["value"])
    return body
