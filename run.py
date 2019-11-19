import logging

import connexion

logging.basicConfig(level=logging.DEBUG)
app = connexion.FlaskApp(__name__)
app.add_api('api.yml')

if __name__ == "__main__":
    app.run()
