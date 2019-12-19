from connexion import NoContent
from flask_marshmallow import Schema

from crc import db, ma
from crc.models import WorkflowModel, WorkflowSchema, StudySchema, StudyModel, WorkflowSpecSchema, WorkflowSpecModel, \
    WorkflowStatus, Task, TaskSchema
from crc.workflow_processor import WorkflowProcessor


class ApiError:
    def __init__(self, code, message):
        self.code = code
        self.message = message


class ApiErrorSchema(ma.Schema):
    class Meta:
        fields = ("code", "message")


def all_studies():
    #todo: Limit returned studies to a user
    schema = StudySchema(many=True)
    return schema.dump(db.session.query(StudyModel).all())


def get_study(study_id):
    study = db.session.query(StudyModel).filter_by(id=study_id).first()
    schema = StudySchema()
    if study is None:
        return NoContent, 404
    return schema.dump(study)


def all_specifications():
    schema = WorkflowSpecSchema(many=True)
    return schema.dump(db.session.query(WorkflowSpecModel).all())


def post_update_study_from_protocol_builder(study_id):
    #todo: Actually get data from an external service here
    return NoContent, 304


def get_study_workflows(study_id):
    workflows = db.session.query(WorkflowModel).filter_by(study_id=study_id).all()
    schema = WorkflowSchema(many=True)
    return schema.dump(workflows)


def add_workflow_to_study(study_id, body):
    workflow_spec_model = db.session.query(WorkflowSpecModel).filter_by(id=body["id"]).first()
    if workflow_spec_model is None:
        error = ApiError('unknown_spec', 'The specification "' + body['id'] + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404

    processor = WorkflowProcessor.create(workflow_spec_model.id)
    workflow = WorkflowModel(bpmn_workflow_json=processor.serialize(),
                             status=processor.get_status(),
                             study_id=study_id,
                             workflow_spec_id=workflow_spec_model.id)
    db.session.add(workflow)
    db.session.commit()
    return get_study_workflows(study_id)


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

