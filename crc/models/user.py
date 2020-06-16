import datetime

import jwt
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from crc import db, app
from crc.api.common import ApiError


class UserModel(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String, unique=True)
    email_address = db.Column(db.String)
    display_name = db.Column(db.String)
    affiliation = db.Column(db.String, nullable=True)
    eppn = db.Column(db.String, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    title = db.Column(db.String, nullable=True)

    # TODO: Add Department and School


    def encode_auth_token(self):
        """
        Generates the Auth Token
        :return: string
        """
        hours = float(app.config['TOKEN_AUTH_TTL_HOURS'])
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=hours, minutes=0, seconds=0),
            'iat': datetime.datetime.utcnow(),
            'sub': self.uid
        }
        return jwt.encode(
            payload,
            app.config.get('TOKEN_AUTH_SECRET_KEY'),
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
            payload = jwt.decode(auth_token, app.config.get('TOKEN_AUTH_SECRET_KEY'), algorithms='HS256')
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

