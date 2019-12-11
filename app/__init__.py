import logging
import connexion
from app.api import workflows

logging.basicConfig(level=logging.INFO)

connexion_app = connexion.FlaskApp(__name__)
connexion_app.add_api('api.yml')

app = connexion_app.app
app.config.from_object('config.default')