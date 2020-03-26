from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import func

from crc import db
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudy


class StudyModel(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now())
    protocol_builder_status = db.Column(db.Enum(ProtocolBuilderStatus))
    primary_investigator_id = db.Column(db.String, nullable=True)
    sponsor = db.Column(db.String, nullable=True)
    hsr_number = db.Column(db.String, nullable=True)
    ind_number = db.Column(db.String, nullable=True)
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False)
    investigator_uids = db.Column(db.ARRAY(db.String), nullable=True)
    inactive = db.Column(db.Boolean, default=False)
    requirements = db.Column(db.ARRAY(db.Integer), nullable=True)

    def update_from_protocol_builder(self, pbs: ProtocolBuilderStudy):
        self.hsr_number = pbs.HSRNUMBER
        self.title = pbs.TITLE
        self.user_uid = pbs.NETBADGEID
        self.last_updated = pbs.DATE_MODIFIED
        self.protocol_builder_status = ProtocolBuilderStatus.DRAFT
        self.inactive = False

        if pbs.HSRNUMBER:  # And Up load complete?
            self.protocol_builder_status = ProtocolBuilderStatus.REVIEW_COMPLETE
        elif pbs.Q_COMPLETE:
            self.protocol_builder_status = ProtocolBuilderStatus.IN_PROCESS


class StudyModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = StudyModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys

    protocol_builder_status = EnumField(ProtocolBuilderStatus)
