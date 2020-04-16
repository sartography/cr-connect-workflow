import os
from os import environ

basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
CORS_ENABLED = False
DEVELOPMENT = environ.get('DEVELOPMENT', default="true") == "true"
TESTING = environ.get('TESTING', default="false") == "true"
PRODUCTION = (environ.get('PRODUCTION', default="false") == "true") or (not DEVELOPMENT and not TESTING)

DB_HOST = environ.get('DB_HOST', default="localhost")
DB_PORT = environ.get('DB_PORT', default="5432")
DB_NAME = environ.get('DB_NAME', default="crc_dev")
DB_USER = environ.get('DB_USER', default="crc_user")
DB_PASSWORD = environ.get('DB_PASSWORD', default="crc_pass")
SQLALCHEMY_DATABASE_URI = environ.get(
    'SQLALCHEMY_DATABASE_URI',
    default="postgresql://%s:%s@%s:%s/%s" % (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
)
TOKEN_AUTH_TTL_HOURS = 2
TOKEN_AUTH_SECRET_KEY = environ.get('TOKEN_AUTH_SECRET_KEY', default="Shhhh!!! This is secret!  And better darn well not show up in prod.")
FRONTEND_AUTH_CALLBACK = environ.get('FRONTEND_AUTH_CALLBACK', default="http://localhost:4200/session")
SWAGGER_AUTH_KEY = environ.get('SWAGGER_AUTH_KEY', default="SWAGGER")

#: Default attribute map for single signon.
SSO_ATTRIBUTE_MAP = {
    'eppn': (False, 'eppn'),  # dhf8r@virginia.edu
    'uid': (True, 'uid'),  # dhf8r
    'givenName': (False, 'first_name'),  # Daniel
    'mail': (False, 'email_address'),  # dhf8r@Virginia.EDU
    'sn': (False, 'last_name'),  # Funk
    'affiliation': (False, 'affiliation'),  # 'staff@virginia.edu;member@virginia.edu'
    'displayName': (False, 'display_name'),  # Daniel Harold Funk
    'title': (False, 'title')  # SOFTWARE ENGINEER V
}

# %s/%i placeholders expected for uva_id and study_id in various calls.
PB_BASE_URL = environ.get('PB_BASE_URL', default="http://localhost:5001/pb/")
PB_USER_STUDIES_URL = environ.get('PB_USER_STUDIES_URL', default=PB_BASE_URL + "user_studies?uva_id=%s")
PB_INVESTIGATORS_URL = environ.get('PB_INVESTIGATORS_URL', default=PB_BASE_URL + "investigators?studyid=%i")
PB_REQUIRED_DOCS_URL = environ.get('PB_REQUIRED_DOCS_URL', default=PB_BASE_URL + "required_docs?studyid=%i")
PB_STUDY_DETAILS_URL = environ.get('PB_STUDY_DETAILS_URL', default=PB_BASE_URL + "study?studyid=%i")

print('=== USING DEFAULT CONFIG: ===')
print('DB_HOST = ', DB_HOST)
print('DEVELOPMENT = ', DEVELOPMENT)
print('TESTING = ', TESTING)
print('PB_BASE_URL = ', PB_BASE_URL)
