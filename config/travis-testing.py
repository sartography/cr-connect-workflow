import os
basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
DEVELOPMENT = True
TESTING = True
SQLALCHEMY_DATABASE_URI = "postgresql://postgres:@localhost:5432/crc_test"
TOKEN_AUTH_TTL_HOURS = 2
TOKEN_AUTH_SECRET_KEY = "Shhhh!!! This is secret!  And better darn well not show up in prod."
FRONTEND_AUTH_CALLBACK = "http://localhost:4200/session"  # Not Required
PB_ENABLED = False

print('+++ USING TRAVIS TESTING CONFIG: +++')
print('SQLALCHEMY_DATABASE_URI = ', SQLALCHEMY_DATABASE_URI)
print('DEVELOPMENT = ', DEVELOPMENT)
print('TESTING = ', TESTING)
print('FRONTEND_AUTH_CALLBACK = ', FRONTEND_AUTH_CALLBACK)
