#!/bin/bash

# run migrations
export FLASK_APP=./crc/__init__.py
pipenv run flask db upgrade

if [ "$RESET_DB" = "true" ]; then
  echo 'Resetting database...'
  pipenv run flask load-example-data
fi

pipenv run python ./run.py
