import logging.config
import os
import traceback

import click
import sentry_sdk

import connexion
from SpiffWorkflow import WorkflowException
from SpiffWorkflow.exceptions import WorkflowTaskExecException
from connexion import ProblemException
from flask import Response
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sentry_sdk.integrations.flask import FlaskIntegration
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.middleware.proxy_fix import ProxyFix


connexion_app = connexion.FlaskApp(__name__)

app = connexion_app.app
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)  # respect the X-Forwarded-Proto if behind a proxy.
app.config.from_object('config.default')

if "TESTING" in os.environ and os.environ["TESTING"] == "true":
    app.config.from_object('config.testing')
    app.config.from_pyfile('../config/testing.py')
    import logging
    logging.basicConfig(level=logging.INFO)
else:
    app.config.root_path = app.instance_path
    app.config.from_pyfile('config.py', silent=True)
    from config.logging import logging_config
    logging.config.dictConfig(logging_config)


db = SQLAlchemy(app)
""":type: sqlalchemy.orm.SQLAlchemy"""

session = db.session
""":type: sqlalchemy.orm.Session"""
scheduler = BackgroundScheduler()

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Mail settings
mail = Mail(app)

migrate = Migrate(app, db)
ma = Marshmallow(app)

from crc import models
from crc import api
from crc.api import admin
from crc.services.workflow_service import WorkflowService
connexion_app.add_api('api.yml', base_path='/v1.0')
# connexion_app.add_api('api_v2.yml', base_path='/v2.0')

# from crc.shared.test_blueprint import test_blueprint
# app.register_blueprint(test_blueprint)
from flask_bpmn.test_blueprint_file import test_blueprint
app.register_blueprint(test_blueprint)

# needed function to avoid circular import
def process_waiting_tasks():
    with app.app_context():
        WorkflowService.do_waiting()


@app.before_first_request
def init_scheduler():
    if app.config['PROCESS_WAITING_TASKS']:
        scheduler.add_job(process_waiting_tasks, 'interval', minutes=1)
        scheduler.add_job(WorkflowService().process_erroring_workflows, 'interval', minutes=1440)
        scheduler.start()


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
    error = ApiError(code=exception.title, message=exception.detail, status_code=exception.status)
    return Response(ApiErrorSchema().dumps(error), status=500, mimetype="text/json")


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
def clear_db():
    """Load example data into the database."""
    from example_data import ExampleDataLoader
    ExampleDataLoader.clean_db()

@app.cli.command()
@click.argument("study_id")
@click.argument("category", required=False)
@click.argument("spec_id", required=False)
def validate_all(study_id, category=None, spec_id=None):
    """Step through all the local workflows and validate them, returning any errors. This make take forever.
    Please provide a real study id to use for validation, an optional category can be specified to only validate
    that category, and you can further specify a specific spec, if needed."""
    from crc.services.workflow_service import WorkflowService
    from crc.services.workflow_processor import WorkflowProcessor
    from crc.services.workflow_spec_service import WorkflowSpecService
    from crc.api.common import ApiError
    from crc.models.study import StudyModel
    from crc.models.user import UserModel
    from flask import g

    logging.root.removeHandler(logging.root.handlers[0])

    study = session.query(StudyModel).filter(StudyModel.id == study_id).first()
    g.user = session.query(UserModel).filter(UserModel.uid == study.user_uid).first()
    g.token = "anything_is_fine_just_need_something."
    specs = WorkflowSpecService().get_specs()
    statuses = WorkflowProcessor.run_master_spec(WorkflowSpecService().master_spec, study)

    for spec in specs:
        if spec_id and spec_id != spec.id:
            continue
        if category and (not spec.category or spec.category.display_name != category):
            continue

        print("-----------------------------------------")
        print(f"{spec.category.display_name} / {spec.id}")
        print("-----------------------------------------")

        if spec.id in statuses and statuses[spec.id]['status'] == 'disabled':
            print(f"Skipping {spec.id} in category {spec.category.display_name}, it is disabled for this study.")
            continue
        try:
            WorkflowService.test_spec(spec.id, validate_study_id=study_id)
            print('Success!')
        except ApiError as e:
            if e.code == 'disabled_workflow':
                print(f"Skipping {spec.id} in category {spec.category.display_name}, it is disabled for this study.")
            else:
                print(f"API Error {e.code}, validate workflow {spec.id} in Category {spec.category.display_name}. {e.message}")
                for t in e.task_trace:
                    print(f"---> {t}")
                continue
        except WorkflowTaskExecException as e:
            print(f"Workflow Error, {e}, in Task {e.task.name} validate workflow {spec.id} in Category {spec.category.display_name}")
            for t in e.task_trace:
                print(f"---> {t}")
            continue
        except Exception as e:
            print(f"Unexpected Error ({e.__class__.__name__}), {e} validate workflow {spec.id} in Category {spec.category.display_name}")
            # printing stack trace
            traceback.print_exc()
            print(e)
            return
