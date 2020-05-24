import os
import re
from os import environ

basedir = os.path.abspath(os.path.dirname(__file__))

JSON_SORT_KEYS = False  # CRITICAL.  Do not sort the data when returning values to the front end.

NAME = "CR Connect Workflow"
FLASK_PORT = environ.get('PORT0') or environ.get('FLASK_PORT', default="5000")
CORS_ALLOW_ORIGINS = re.split(r',\s*', environ.get('CORS_ALLOW_ORIGINS', default="localhost:4200, localhost:5002"))
DEVELOPMENT = environ.get('DEVELOPMENT', default="true") == "true"
TESTING = environ.get('TESTING', default="false") == "true"
PRODUCTION = (environ.get('PRODUCTION', default="false") == "true") or (not DEVELOPMENT and not TESTING)

# Add trailing slash to base path
APPLICATION_ROOT = re.sub(r'//', '/', '/%s/' % environ.get('APPLICATION_ROOT', default="/").strip('/'))

DB_HOST = environ.get('DB_HOST', default="localhost")
DB_PORT = environ.get('DB_PORT', default="5432")
DB_NAME = environ.get('DB_NAME', default="crc_dev")
DB_USER = environ.get('DB_USER', default="crc_user")
DB_PASSWORD = environ.get('DB_PASSWORD', default="crc_pass")
SQLALCHEMY_DATABASE_URI = environ.get(
    'SQLALCHEMY_DATABASE_URI',
    default="postgresql://%s:%s@%s:%s/%s" % (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
)
TOKEN_AUTH_TTL_HOURS = environ.get('TOKEN_AUTH_TTL_HOURS', default=4)
TOKEN_AUTH_SECRET_KEY = environ.get('TOKEN_AUTH_SECRET_KEY', default="Shhhh!!! This is secret!  And better darn well not show up in prod.")
FRONTEND_AUTH_CALLBACK = environ.get('FRONTEND_AUTH_CALLBACK', default="http://localhost:4200/session")
SWAGGER_AUTH_KEY = environ.get('SWAGGER_AUTH_KEY', default="SWAGGER")

# %s/%i placeholders expected for uva_id and study_id in various calls.
PB_ENABLED = environ.get('PB_ENABLED', default=True)
PB_BASE_URL = environ.get('PB_BASE_URL', default="http://localhost:5001/pb/").strip('/') + '/'  # Trailing slash required
PB_USER_STUDIES_URL = environ.get('PB_USER_STUDIES_URL', default=PB_BASE_URL + "user_studies?uva_id=%s")
PB_INVESTIGATORS_URL = environ.get('PB_INVESTIGATORS_URL', default=PB_BASE_URL + "investigators?studyid=%i")
PB_REQUIRED_DOCS_URL = environ.get('PB_REQUIRED_DOCS_URL', default=PB_BASE_URL + "required_docs?studyid=%i")
PB_STUDY_DETAILS_URL = environ.get('PB_STUDY_DETAILS_URL', default=PB_BASE_URL + "study?studyid=%i")

LDAP_URL = environ.get('LDAP_URL', default="ldap.virginia.edu").strip('/')  # No trailing slash or http://
LDAP_TIMEOUT_SEC = environ.get('LDAP_TIMEOUT_SEC', default=3)
print('=== USING DEFAULT CONFIG: ===')
print('DB_HOST = ', DB_HOST)
print('CORS_ALLOW_ORIGINS = ', CORS_ALLOW_ORIGINS)
print('DEVELOPMENT = ', DEVELOPMENT)
print('TESTING = ', TESTING)
print('PRODUCTION = ', PRODUCTION)
print('PB_BASE_URL = ', PB_BASE_URL)
print('LDAP_URL = ', LDAP_URL)
print('APPLICATION_ROOT = ', APPLICATION_ROOT)

