import logging
import os

import connexion
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

logging.basicConfig(level=logging.INFO)

connexion_app = connexion.FlaskApp(__name__)

app = connexion_app.app
app.config.from_object('config.default')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

migrate = Migrate(app, db)
ma = Marshmallow(app)

from crc import models
from crc import api

connexion_app.add_api('api.yml', base_path='/v1.0')

# Convert list of allowed origins to list of regexes
origins_re = [r"^https?:\/\/%s(.*)" % o.replace('.', '\.') for o in app.config['CORS_ALLOW_ORIGINS']]
cors = CORS(connexion_app.app, origins=origins_re)

print('=== USING THESE CONFIG SETTINGS: ===')
print('DB_HOST = ', )
print('CORS_ALLOW_ORIGINS = ', app.config['CORS_ALLOW_ORIGINS'])
print('DEVELOPMENT = ', app.config['DEVELOPMENT'])
print('TESTING = ', app.config['TESTING'])
print('PRODUCTION = ', app.config['PRODUCTION'])
print('PB_BASE_URL = ', app.config['PB_BASE_URL'])
print('LDAP_URL = ', app.config['LDAP_URL'])
print('APPLICATION_ROOT = ', app.config['APPLICATION_ROOT'])
print('PB_ENABLED = ', app.config['PB_ENABLED'])

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
