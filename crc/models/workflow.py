import enum

import marshmallow
from marshmallow import EXCLUDE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import func
from sqlalchemy.orm import backref

from crc import db
from crc.models.file import FileDataModel


class WorkflowSpecCategoryModel(db.Model):
    __tablename__ = 'workflow_spec_category'
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String)
    display_order = db.Column(db.Integer)
    admin = db.Column(db.Boolean)


class WorkflowSpecCategoryModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = WorkflowSpecCategoryModel
        load_instance = True
        include_relationships = True


class WorkflowSpecModel(db.Model):
    __tablename__ = 'workflow_spec'
    id = db.Column(db.String, primary_key=True)
    display_name = db.Column(db.String)
    display_order = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('workflow_spec_category.id'), nullable=True)
    category = db.relationship("WorkflowSpecCategoryModel")
    is_master_spec = db.Column(db.Boolean, default=False)
    standalone = db.Column(db.Boolean, default=False)
    library = db.Column(db.Boolean, default=False)


class WorkflowLibraryModel(db.Model):
   __tablename__ = 'workflow_library'
   id = db.Column(db.Integer, primary_key=True)
   workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'), nullable=True)
   library_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'), nullable=True)
   parent = db.relationship(WorkflowSpecModel,
                                   primaryjoin=workflow_spec_id==WorkflowSpecModel.id,
                                  backref=backref('libraries',cascade='all, delete'))
   library = db.relationship(WorkflowSpecModel,primaryjoin=library_spec_id==WorkflowSpecModel.id,
                                  backref=backref('parents',cascade='all, delete'))


class WorkflowSpecModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = WorkflowSpecModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
        unknown = EXCLUDE

    category = marshmallow.fields.Nested(WorkflowSpecCategoryModelSchema, dump_only=True)
    libraries = marshmallow.fields.Function(lambda obj: [{'id':x.library.id,
                                                          'display_name':x.library.display_name} for x in
                                                          obj.libraries] )
    parents = marshmallow.fields.Function(lambda obj: [{'id':x.parent.id,
                                                          'display_name':x.parent.display_name} for x in
                                                          obj.parents] )

class WorkflowState(enum.Enum):
    hidden = "hidden"
    disabled = "disabled"
    required = "required"
    optional = "optional"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @staticmethod
    def list():
        return list(map(lambda c: c.value, WorkflowState))


class WorkflowStatus(enum.Enum):
    not_started = "not_started"
    user_input_required = "user_input_required"
    waiting = "waiting"
    complete = "complete"
    erroring = "erroring"


class WorkflowSpecDependencyFile(db.Model):
    """Connects to a workflow to test the version of the specification files it depends on to execute"""
    file_data_id = db.Column(db.Integer, db.ForeignKey(FileDataModel.id), primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey("workflow.id"), primary_key=True)

    file_data = db.relationship(FileDataModel)



class WorkflowLibraryModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = WorkflowLibraryModel
        load_instance = True
        include_relationships = True

    library = marshmallow.fields.Nested('WorkflowSpecModelSchema')

class WorkflowModel(db.Model):
    __tablename__ = 'workflow'
    id = db.Column(db.Integer, primary_key=True)
    bpmn_workflow_json = db.Column(db.JSON)
    status = db.Column(db.Enum(WorkflowStatus))
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    study = db.relationship("StudyModel", backref='workflow')
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    workflow_spec = db.relationship("WorkflowSpecModel")
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now())
    user_id = db.Column(db.String, default=None)
    # Order By is important or generating hashes on reviews.
    dependencies = db.relationship(WorkflowSpecDependencyFile, cascade="all, delete, delete-orphan",
                                   order_by="WorkflowSpecDependencyFile.file_data_id")

    def spec_version(self):
        dep_ids = list(dep.file_data_id for dep in self.dependencies)
        return "-".join(str(dep_ids))
