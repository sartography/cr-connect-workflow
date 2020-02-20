import os

basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
CORS_ENABLED = False
DEVELOPMENT = True
SQLALCHEMY_DATABASE_URI = "postgresql://crc_user:crc_pass@localhost:5432/crc_dev"
TOKEN_AUTH_TTL_HOURS = 2
TOKEN_AUTH_SECRET_KEY = "Shhhh!!! This is secret!  And better darn well not show up in prod."
FRONTEND_AUTH_CALLBACK = "http://localhost:4200"

#: Default attribute map for single signon.
SSO_ATTRIBUTE_MAP = {
    'eppn': (False, 'eppn'),  # dhf8r@virginia.edu
    'uid': (True, 'uid'),  # dhf8r
    'givenName': (False, 'givenName'), # Daniel
    'mail': (False, 'email'), # dhf8r@Virginia.EDU
    'sn': (False, 'surName'), # Funk
    'affiliation': (False, 'affiliation'), #  'staff@virginia.edu;member@virginia.edu'
    'displayName': (False, 'displayName'), # Daniel Harold Funk
    'title': (False, 'title')  # SOFTWARE ENGINEER V
}

# %s/%i placeholders expected for uva_id and study_id in various calls.
PB_USER_STUDIES_URL = "http://workflow.sartography.com:5001/pb/user_studies?uva_id=%s"
PB_INVESTIGATORS_URL = "http://workflow.sartography.com:5001/pb/investigators?studyid=%i"
PB_REQUIRED_DOCS_URL = "http://workflow.sartography.com:5001/pb/required_docs?studyid=%i"
PB_STUDY_DETAILS_URL = "http://workflow.sartography.com:5001/pb/study?studyid=%i"
