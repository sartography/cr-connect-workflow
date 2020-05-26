import os
from os import environ

basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
DEVELOPMENT = True
TESTING = True
TOKEN_AUTH_TTL_HOURS = 2
TOKEN_AUTH_SECRET_KEY = "Shhhh!!! This is secret!  And better darn well not show up in prod."
FRONTEND_AUTH_CALLBACK = "http://localhost:4200/session"  # Not Required

DB_HOST = environ.get('DB_HOST', default="localhost")
DB_PORT = environ.get('DB_PORT', default="5432")
DB_NAME = environ.get('DB_NAME', default="crc_dev")
DB_USER = environ.get('DB_USER', default="crc_user")
DB_PASSWORD = environ.get('DB_PASSWORD', default="crc_pass")
SQLALCHEMY_DATABASE_URI = environ.get(
    'SQLALCHEMY_DATABASE_URI',
    default="postgresql://%s:%s@%s:%s/%s" % (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
)

print('+++ USING TRAVIS TESTING CONFIG: +++')
print('DEVELOPMENT = ', DEVELOPMENT)
print('TESTING = ', TESTING)
print('FRONTEND_AUTH_CALLBACK = ', FRONTEND_AUTH_CALLBACK)
print('DB_HOST = ', DB_HOST)
