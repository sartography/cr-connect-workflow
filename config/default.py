import os
import re
from os import environ

basedir = os.path.abspath(os.path.dirname(__file__))

JSON_SORT_KEYS = False  # CRITICAL.  Do not sort the data when returning values to the front end.

# The API_TOKEN is used to ensure that the
# workflow sync can work without a lot of
# back and forth.
# you may want to change this to something simple for testing!!
# NB, if you change this in the local endpoint,
# it needs to be changed in the remote endpoint as well
API_TOKEN = environ.get('API_TOKEN', default = 'af95596f327c9ecc007b60414fc84b61')

NAME = "CR Connect Workflow"
SERVER_NAME = environ.get('SERVER_NAME', default="localhost:5000")
INSTANCE_NAME = environ.get('INSTANCE_NAME', default='development')
DEFAULT_PORT = "5000"
FLASK_PORT = environ.get('PORT0') or environ.get('FLASK_PORT', default=DEFAULT_PORT)
FRONTEND = environ.get('FRONTEND', default="localhost:4200")
BPMN = environ.get('BPMN', default="localhost:5002")
CORS_DEFAULT = f'{FRONTEND}, {BPMN}'
CORS_ALLOW_ORIGINS = re.split(r',\s*', environ.get('CORS_ALLOW_ORIGINS', default=CORS_DEFAULT))
TESTING = environ.get('TESTING', default="false") == "true"
PRODUCTION = environ.get('PRODUCTION', default="false") == "true"
DEVELOPMENT = environ.get('DEVELOPMENT', default="false") == "true"
TEST_UID = environ.get('TEST_UID', default="dhf8r")
ADMIN_UIDS = re.split(r',\s*', environ.get('ADMIN_UIDS', default="dhf8r,kcm4zc,cah3us"))
SUPERUSER_UIDS = re.split(r',\s*', environ.get('SUPERUSER_UIDS', default="dhf8r,kcm4zc,cah3us"))
DEFAULT_UID = environ.get('DEFAULT_UID', default="dhf8r")
CRC_SUPPORT_EMAIL = environ.get('CRC_SUPPORT_EMAIL', default="CRCONNECTSUPPORT@uvahealth.org")
CRC_SYSTEM_ADMIN_EMAIL = environ.get('CRC_SYSTEM_ADMIN_EMAIL', default="kcm4zc@uvahealth.org")
WAITING_CHECK_INTERVAL = int(environ.get('WAITING_CHECK_INTERVAL', default=10))  # in minutes
FAILING_CHECK_INTERVAL = int(environ.get('FAILING_CHECK_INTERVAL', default=1440))  # in minutes

# Sentry flag
ENABLE_SENTRY = environ.get('ENABLE_SENTRY', default="false") == "true"  # To be removed soon
SENTRY_ENVIRONMENT = environ.get('SENTRY_ENVIRONMENT', None)

# Add trailing slash to base path
APPLICATION_ROOT = re.sub(r'//', '/', '/%s/' % environ.get('APPLICATION_ROOT', default="/").strip('/'))

DB_HOST = environ.get('DB_HOST', default="localhost")
DB_PORT = environ.get('DB_PORT', default="5432")
DB_NAME = environ.get('DB_NAME', default="crc_dev")
DB_USER = environ.get('DB_USER', default="crc_user")
DB_PASSWORD = environ.get('DB_PASSWORD', default="crc_pass")
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = environ.get(
    'SQLALCHEMY_DATABASE_URI',
    default="postgresql://%s:%s@%s:%s/%s" % (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
)


TOKEN_AUTH_TTL_HOURS = float(environ.get('TOKEN_AUTH_TTL_HOURS', default=24))
SECRET_KEY = environ.get('SECRET_KEY', default="Shhhh!!! This is secret!  And better darn well not show up in prod.")
# SWAGGER_AUTH_KEY = environ.get('SWAGGER_AUTH_KEY', default="SWAGGER")
# %s/%i placeholders expected for uva_id and study_id in various calls.
PB_ENABLED = environ.get('PB_ENABLED', default="false") == "true"
PB_BASE_URL = environ.get('PB_BASE_URL', default="http://localhost:5001/v2.0/").strip('/') + '/'  # Trailing slash required
PB_USER_STUDIES_URL = environ.get('PB_USER_STUDIES_URL', default=PB_BASE_URL + "user_studies?uva_id=%s")
PB_INVESTIGATORS_URL = environ.get('PB_INVESTIGATORS_URL', default=PB_BASE_URL + "investigators?studyid=%i")
PB_REQUIRED_DOCS_URL = environ.get('PB_REQUIRED_DOCS_URL', default=PB_BASE_URL + "required_docs?studyid=%i")
PB_STUDY_DETAILS_URL = environ.get('PB_STUDY_DETAILS_URL', default=PB_BASE_URL + "study?studyid=%i")
PB_SPONSORS_URL = environ.get('PB_SPONSORS_URL', default=PB_BASE_URL + "sponsors?studyid=%i")
PB_IRB_INFO_URL = environ.get('PB_IRB_INFO_URL', default=PB_BASE_URL + "current_irb_info/%i")
PB_CHECK_STUDY_URL = environ.get('PB_CHECK_STUDY_URL', default=PB_BASE_URL + "check_study/%i")
PB_PRE_REVIEW_URL = environ.get('PB_PRE_REVIEW_URL', default=PB_BASE_URL + "pre_reviews/%i")

# Only studies with a creation date greater than or equal to PB_MIN_DATE will be imported.
PB_MIN_DATE = environ.get('PB_MIN_DATE', default="2020-01-01T00:00:00.000Z")

# Ldap Configuration
LDAP_URL = environ.get('LDAP_URL', default="ldap.virginia.edu").strip('/')  # No trailing slash or http://
LDAP_TIMEOUT_SEC = int(environ.get('LDAP_TIMEOUT_SEC', default=1))
LDAP_USER = environ.get('LDAP_USER', default='')
LDAP_PASS = environ.get('LDAP_PASS', default='')

# Github settings
GITHUB_TOKEN = environ.get('GITHUB_TOKEN', None)
GITHUB_REPO = environ.get('GITHUB_REPO', None)
TARGET_BRANCH = environ.get('TARGET_BRANCH', None)

# Git settings, used by git_service
# Among other things, we use these to build a remote URL like https://username:password@host/path.git
GIT_REMOTE_SERVER = environ.get('GIT_REMOTE_SERVER', None)  # example: 'github.com'
GIT_REMOTE_PATH = environ.get('GIT_REMOTE_PATH', None)  # example: 'sartography/crconnect-workflow-specs
GIT_BRANCH = environ.get('GIT_BRANCH', None)  # example: 'main'
GIT_MERGE_BRANCH = environ.get('GIT_MERGE_BRANCH', None)  # Example: 'staging'
GIT_USER_NAME = environ.get('GIT_USER_NAME', None)
GIT_USER_PASS = environ.get('GIT_USER_PASS', None)
GIT_DISPLAY_PUSH = environ.get('GIT_DISPLAY_PUSH', False)
GIT_DISPLAY_MERGE = environ.get('GIT_DISPLAY_MERGE', False)


# Email configuration
DEFAULT_SENDER = 'crconnect2@virginia.edu'
FALLBACK_EMAILS = ['askresearch@virginia.edu', 'sartographysupport@googlegroups.com']
MAIL_DEBUG = environ.get('MAIL_DEBUG', default=True)
MAIL_SERVER = environ.get('MAIL_SERVER', default='smtp.mailtrap.io')
MAIL_PORT = environ.get('MAIL_PORT', default=2525)
MAIL_USE_SSL = environ.get('MAIL_USE_SSL', default=False)
MAIL_USE_TLS = environ.get('MAIL_USE_TLS', default=False)
MAIL_USERNAME = environ.get('MAIL_USERNAME', default='')
MAIL_PASSWORD = environ.get('MAIL_PASSWORD', default='')

# Local file path
SYNC_FILE_ROOT = environ.get('SYNC_FILE_ROOT', default='tests/data/IMPORT_TEST')

# Turn on/off processing waiting tasks
PROCESS_WAITING_TASKS = environ.get('PROCESS_WAITING_TASKS', default='true')

CAN_TIME_IT = environ.get('CAN_TIME_IT', default='false') == 'true'
