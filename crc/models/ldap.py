from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import EXCLUDE
from sqlalchemy import func, inspect

from crc import db


class LdapModel(db.Model):
    uid = db.Column(db.String, primary_key=True)
    display_name = db.Column(db.String)
    given_name = db.Column(db.String)
    email_address = db.Column(db.String)
    telephone_number = db.Column(db.String)
    title = db.Column(db.String)
    department = db.Column(db.String)
    affiliation = db.Column(db.String)
    sponsor_type = db.Column(db.String)
    date_cached = db.Column(db.DateTime(timezone=True), default=func.now())

    @classmethod
    def from_entry(cls, entry):
        return LdapModel(uid=entry.uid.value,
                         display_name=entry.displayName.value,
                         given_name=", ".join(entry.givenName),
                         email_address=entry.mail.value,
                         telephone_number=entry.telephoneNumber.value,
                         title=", ".join(entry.title),
                         department=", ".join(entry.uvaDisplayDepartment),
                         affiliation=", ".join(entry.uvaPersonIAMAffiliation),
                         sponsor_type=", ".join(entry.uvaPersonSponsoredType))


class LdapSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = LdapModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
        unknown = EXCLUDE
