from crc import db
from crc.models.workflow import WorkflowModel, WorkflowModelSchema, WorkflowSpecModelSchema, WorkflowSpecModel, \
    Task, TaskSchema
from crc.workflow_processor import WorkflowProcessor


def all_specifications():
    schema = WorkflowSpecModelSchema(many=True)
    return schema.dump(db.session.query(WorkflowSpecModel).all())


def get_workflow(workflow_id):
    schema = WorkflowModelSchema()
    workflow = db.session.query(WorkflowModel).filter_by(id=workflow_id).first()
    return schema.dump(workflow)


def delete(workflow_id):
    db.session.query(WorkflowModel).filter_by(id=workflow_id).delete()
    db.session.commit()


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
    workflow_spec_model = db.session.query(WorkflowSpecModel).filter_by(id=body["id"]).first()
    task = TaskSchema().load(body)
    if task.form:
        for field in task.form["fields"]:
            print("Setting " + field["id"] + " to " + field["value"])
    return body
