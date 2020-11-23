import json
import logging
import os
import sentry_sdk

import connexion
from connexion import ProblemException
from flask import Response
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sentry_sdk.integrations.flask import FlaskIntegration

logging.basicConfig(level=logging.INFO)

connexion_app = connexion.FlaskApp(__name__)

app = connexion_app.app
app.config.from_object('config.default')

if "TESTING" in os.environ and os.environ["TESTING"] == "true":
    app.config.from_object('config.testing')
    app.config.from_pyfile('../config/testing.py')
else:
    app.config.root_path = app.instance_path
    app.config.from_pyfile('config.py', silent=True)


db = SQLAlchemy(app)
""":type: sqlalchemy.orm.SQLAlchemy"""

session = db.session
""":type: sqlalchemy.orm.Session"""

# Mail settings
mail = Mail(app)

migrate = Migrate(app, db)
ma = Marshmallow(app)

from crc import models
from crc import api
from crc.api import admin

connexion_app.add_api('api.yml', base_path='/v1.0')


# Convert list of allowed origins to list of regexes
origins_re = [r"^https?:\/\/%s(.*)" % o.replace('.', '\.') for o in app.config['CORS_ALLOW_ORIGINS']]
cors = CORS(connexion_app.app, origins=origins_re)

# Sentry error handling
if app.config['SENTRY_ENVIRONMENT']:
    sentry_sdk.init(
        environment=app.config['SENTRY_ENVIRONMENT'],
        dsn="https://25342ca4e2d443c6a5c49707d68e9f40@o401361.ingest.sentry.io/5260915",
        integrations=[FlaskIntegration()]
    )


# Connexion Error handling
def render_errors(exception):
    from crc.api.common import ApiError, ApiErrorSchema
    error = ApiError(code=exception.title, message=exception.details, status_code=exception.status)
    return Response(ApiErrorSchema().dump(error), status=401, mimetype="application/json")


connexion_app.add_error_handler(ProblemException, render_errors)



print('=== USING THESE CONFIG SETTINGS: ===')
print('APPLICATION_ROOT = ', app.config['APPLICATION_ROOT'])
print('CORS_ALLOW_ORIGINS = ', app.config['CORS_ALLOW_ORIGINS'])
print('DB_HOST = ', app.config['DB_HOST'])
print('LDAP_URL = ', app.config['LDAP_URL'])
print('PB_BASE_URL = ', app.config['PB_BASE_URL'])
print('PB_ENABLED = ', app.config['PB_ENABLED'])
print('PRODUCTION = ', app.config['PRODUCTION'])
print('TESTING = ', app.config['TESTING'])
print('TEST_UID = ', app.config['TEST_UID'])
print('ADMIN_UIDS = ', app.config['ADMIN_UIDS'])

@app.cli.command()
def load_example_data():
    """Load example data into the database."""
    from example_data import ExampleDataLoader
    ExampleDataLoader.clean_db()
    ExampleDataLoader().load_all()


@app.cli.command()
def load_example_rrt_data():
    """Load example data into the database."""
    from example_data import ExampleDataLoader
    ExampleDataLoader.clean_db()
    ExampleDataLoader().load_rrt()

@app.cli.command()
def clear_db():
    """Load example data into the database."""
    from example_data import ExampleDataLoader
    ExampleDataLoader.clean_db()

