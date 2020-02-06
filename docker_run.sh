# run migrations
ENV FLASK_APP=./crc/__init__.py
RUN pipenv run flask db upgrade
RUN pipenv run flask load-example-data
pipenv run python ./run.py
