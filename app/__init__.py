import logging
import connexion
from app.api import workflows

logging.basicConfig(level=logging.DEBUG)
app = connexion.FlaskApp(__name__)
app.add_api('api.yml')

