import os
basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
CORS_ENABLED = False
DEVELOPMENT = True
TESTING = True
SQLALCHEMY_DATABASE_URI = "postgresql://postgres:@localhost:5432/crc_test"
TOKEN_AUTH_TTL_HOURS = 2
TOKEN_AUTH_SECRET_KEY = "Shhhh!!! This is secret!  And better darn well not show up in prod."
FRONTEND_AUTH_CALLBACK = "http://localhost:4200/session"  # Not Required

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
