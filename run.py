import logging

import connexion

logging.basicConfig(level=logging.DEBUG)

app = connexion.App(
    __name__,
    options={"swagger_ui": False}
)

app.add_api('api.yml')

if __name__ == "__main__":
    app.run()
