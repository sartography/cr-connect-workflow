import datetime

import jwt
from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from crc import db, app
from flask_bpmn.api.common import ApiError
from crc.models.ldap import LdapSchema


class UserModel(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String, db.ForeignKey('ldap_model.uid'), unique=True)
    ldap_info = db.relationship("LdapModel")

    def is_admin(self):
        # Currently admin abilities are set in the configuration, but this
        # may change in the future.
        return self.uid in app.config['ADMIN_UIDS']

    def encode_auth_token(self):
        """
        Generates the Auth Token
        :return: string
        """
        hours = float(app.config['TOKEN_AUTH_TTL_HOURS'])
        payload = {
#            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=hours, minutes=0, seconds=0),
#            'iat': datetime.datetime.utcnow(),
            'sub': self.uid
        }
        return jwt.encode(
            payload,
            app.config.get('SECRET_KEY'),
            algorithm='HS256',
        )

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token
        :param auth_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'), algorithms='HS256')
            return payload
        except jwt.ExpiredSignatureError:
            raise ApiError('token_expired', 'The Authentication token you provided expired and must be renewed.')
        except jwt.InvalidTokenError:
            raise ApiError('token_invalid', 'The Authentication token you provided is invalid. You need a new token. ')


class UserModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = UserModel
        load_instance = True
        include_relationships = True
    uid = fields.String()
    is_admin = fields.Method('get_is_admin', dump_only=True)
    ldap_info = fields.Nested(LdapSchema)

    def get_is_admin(self, obj):
        return obj.is_admin()


class AdminSessionModel(db.Model):
    __tablename__ = 'admin_session'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, unique=True)
    admin_impersonate_uid = db.Column(db.String)
