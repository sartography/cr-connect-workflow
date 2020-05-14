import os
basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
DEVELOPMENT = True
TESTING = True
SQLALCHEMY_DATABASE_URI = "postgresql://crc_user:crc_pass@localhost:5432/crc_test"
TOKEN_AUTH_SECRET_KEY = "Shhhh!!! This is secret!  And better darn well not show up in prod."

print('### USING TESTING CONFIG: ###')
print('SQLALCHEMY_DATABASE_URI = ', SQLALCHEMY_DATABASE_URI)
print('DEVELOPMENT = ', DEVELOPMENT)
print('TESTING = ', TESTING)
