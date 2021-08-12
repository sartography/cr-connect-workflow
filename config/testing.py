import os
from os import environ

basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
TESTING = True
SECRET_KEY = "Shhhh!!! This is secret!  And better darn well not show up in prod."

# This is here, for when we are running the E2E Tests in the frontend code bases.
# which will set the TESTING envronment to true, causing this to execute, but we need
# to respect the environment variables in that case.
# when running locally the defaults apply, meaning we use crc_test for doing the tests
# locally, and we don't over-write the database.  Did you read this far? Have a cookie!
PB_ENABLED = environ.get('PB_ENABLED', default="false") == "true"
DB_HOST = environ.get('DB_HOST', default="localhost")
DB_PORT = environ.get('DB_PORT', default="5432")
DB_NAME = environ.get('DB_NAME', default="crc_test")
DB_USER = environ.get('DB_USER', default="crc_user")
DB_PASSWORD = environ.get('DB_PASSWORD', default="crc_pass")
SQLALCHEMY_DATABASE_URI = environ.get(
    'SQLALCHEMY_DATABASE_URI',
    default="postgresql://%s:%s@%s:%s/%s" % (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
)
ADMIN_UIDS = ['dhf8r']

print('### USING TESTING CONFIG: ###')
print('SQLALCHEMY_DATABASE_URI = ', SQLALCHEMY_DATABASE_URI)
print('TESTING = ', TESTING)

#Use the mock ldap.
LDAP_URL = 'mock'
