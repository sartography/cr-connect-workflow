from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from crc import db


class TaskEventModel(db.Model):
    __tablename__ = 'task_event'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=False)
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    spec_version = db.Column(db.String)
    action = db.Column(db.String)
    task_id = db.Column(db.String)
    task_name = db.Column(db.String)
    task_title = db.Column(db.String)
    task_type = db.Column(db.String)
    task_state = db.Column(db.String)
    form_data = db.Column(db.JSON) # And form data submitted when the task was completed.
    mi_type = db.Column(db.String)
    mi_count = db.Column(db.Integer)
    mi_index = db.Column(db.Integer)
    process_name = db.Column(db.String)
    date = db.Column(db.DateTime)


class TaskEventModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TaskEventModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
