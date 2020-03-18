from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from crc import db


class WorkflowStatsModel(db.Model):
    __tablename__ = 'workflow_stats'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=False)
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    spec_version = db.Column(db.String)
    num_tasks_total = db.Column(db.Integer)
    num_tasks_complete = db.Column(db.Integer)
    num_tasks_incomplete = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime)


class WorkflowStatsModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = WorkflowStatsModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys


class TaskEventModel(db.Model):
    __tablename__ = 'task_event'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=False)
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    spec_version = db.Column(db.String)
    task_id = db.Column(db.String)
    task_state = db.Column(db.String)
    date = db.Column(db.DateTime)


class TaskEventModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TaskEventModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
