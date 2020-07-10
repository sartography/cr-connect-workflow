import os
import re
from os import environ

basedir = os.path.abspath(os.path.dirname(__file__))

JSON_SORT_KEYS = False  # CRITICAL.  Do not sort the data when returning values to the front end.

NAME = "CR Connect Workflow"
FLASK_PORT = environ.get('PORT0') or environ.get('FLASK_PORT', default="5000")
CORS_ALLOW_ORIGINS = re.split(r',\s*', environ.get('CORS_ALLOW_ORIGINS', default="localhost:4200, localhost:5002"))
TESTING = environ.get('TESTING', default="false") == "true"
PRODUCTION = (environ.get('PRODUCTION', default="false") == "true")
TEST_UID = environ.get('TEST_UID', default="dhf8r")
ADMIN_UIDS = re.split(r',\s*', environ.get('ADMIN_UIDS', default="dhf8r,ajl2j,cah3us,cl3wf"))

# Sentry flag
ENABLE_SENTRY = environ.get('ENABLE_SENTRY', default="false") == "true"

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
TOKEN_AUTH_TTL_HOURS = float(environ.get('TOKEN_AUTH_TTL_HOURS', default=24))
SECRET_KEY = environ.get('SECRET_KEY', default="Shhhh!!! This is secret!  And better darn well not show up in prod.")
FRONTEND_AUTH_CALLBACK = environ.get('FRONTEND_AUTH_CALLBACK', default="http://localhost:4200/session")
SWAGGER_AUTH_KEY = environ.get('SWAGGER_AUTH_KEY', default="SWAGGER")

# %s/%i placeholders expected for uva_id and study_id in various calls.
PB_ENABLED = environ.get('PB_ENABLED', default="false") == "true"
PB_BASE_URL = environ.get('PB_BASE_URL', default="http://localhost:5001/v2.0/").strip('/') + '/'  # Trailing slash required
PB_USER_STUDIES_URL = environ.get('PB_USER_STUDIES_URL', default=PB_BASE_URL + "user_studies?uva_id=%s")
PB_INVESTIGATORS_URL = environ.get('PB_INVESTIGATORS_URL', default=PB_BASE_URL + "investigators?studyid=%i")
PB_REQUIRED_DOCS_URL = environ.get('PB_REQUIRED_DOCS_URL', default=PB_BASE_URL + "required_docs?studyid=%i")
PB_STUDY_DETAILS_URL = environ.get('PB_STUDY_DETAILS_URL', default=PB_BASE_URL + "study?studyid=%i")

LDAP_URL = environ.get('LDAP_URL', default="ldap.virginia.edu").strip('/')  # No trailing slash or http://
LDAP_TIMEOUT_SEC = int(environ.get('LDAP_TIMEOUT_SEC', default=1))

# Email configuration
DEFAULT_SENDER = 'askresearch@virginia.edu'
FALLBACK_EMAILS = ['askresearch@virginia.edu', 'sartographysupport@googlegroups.com']
MAIL_DEBUG = environ.get('MAIL_DEBUG', default=True)
MAIL_SERVER = environ.get('MAIL_SERVER', default='smtp.mailtrap.io')
MAIL_PORT = environ.get('MAIL_PORT', default=2525)
MAIL_USE_SSL = environ.get('MAIL_USE_SSL', default=False)
MAIL_USE_TLS = environ.get('MAIL_USE_TLS', default=False)
MAIL_USERNAME = environ.get('MAIL_USERNAME', default='')
MAIL_PASSWORD = environ.get('MAIL_PASSWORD', default='')
