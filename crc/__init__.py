import logging
import os

import connexion
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


logging.basicConfig(level=logging.INFO)

connexion_app = connexion.FlaskApp(__name__)

app = connexion_app.app
app.config.from_object('config.default')
#app.config.from_pyfile('config.py')
if "TESTING" in os.environ and os.environ["TESTING"] == "true":
    app.config.from_object('config.testing')
    app.config.from_pyfile('testing.py')
else:
    # load the instance/config.py, if it exists, when not testing
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

connexion_app.add_api('api.yml')
cors = CORS(connexion_app.app)

@app.cli.command()
def load_example_data():
    """Load example data into the database."""
    from example_data import ExampleDataLoader
    ExampleDataLoader.clean_db()
    ExampleDataLoader().load_all()
