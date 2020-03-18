from marshmallow_sqlalchemy import ModelSchema
from crc import db


class IRBDocumentModel(db.Model):
    """Provides a lookup table for information about how to submit IRB documents,
    which are named according to category levels.  These may be linked
    to a ProtocolBuilder required document, which is the irb_required_doc_id """
    __tablename__ = 'irb_document'
    id = db.Column(db.Integer, primary_key=True)
    irb_required_doc_id = db.Column(db.Integer)
    category1 = db.Column(db.String)
    category2 = db.Column(db.String)
    category3 = db.Column(db.String)
    who_uploads = db.Column(db.String)


