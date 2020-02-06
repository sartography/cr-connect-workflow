# run migrations
export FLASK_APP=./crc/__init__.py
pipenv run flask db upgrade
pipenv run flask load-example-data
pipenv run python ./run.py
