import os
basedir = os.path.abspath(os.path.dirname(__file__))

NAME = "CR Connect Workflow"
CORS_ENABLED = False
DEVELOPMENT = True
SQLALCHEMY_DATABASE_URI = "sqlite:////" + os.path.join(basedir, "cr_connect.db")
