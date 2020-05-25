#!/bin/bash

# run migrations
export FLASK_APP=./crc/__init__.py

if [ "$DOWNGRADE_DB" = "true" ]; then
  echo 'Downgrading database...'
  pipenv run flask db downgrade
fi

if [ "$UPGRADE_DB" = "true" ]; then
  echo 'Upgrading database...'
  pipenv run flask db upgrade
fi

if [ "$RESET_DB" = "true" ]; then
  echo 'Resetting database...'
  pipenv run flask load-example-data
fi

pipenv run gunicorn -e SCRIPT_NAME="$APPLICATION_ROOT" --bind 0.0.0.0:$PORT0 wsgi:app
