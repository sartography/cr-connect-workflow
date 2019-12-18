import logging
import os

import connexion
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


db = SQLAlchemy(app)
migrate = Migrate(app, db)
ma = Marshmallow(app)

from crc import models

connexion_app.add_api('api.yml')

@app.cli.command()
def load_example_data():
    """Load example data into the database."""
    from study import ExampleDataLoader
    ExampleDataLoader().load_studies()
