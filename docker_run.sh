#!/bin/bash

# run migrations
export FLASK_APP=/app/crc/__init__.py

if [ "$DOWNGRADE_DB" = "true" ]; then
  echo 'Downgrading database...'
  pipenv run flask db downgrade
fi

if [ "$UPGRADE_DB" = "true" ]; then
  echo 'Upgrading database...'
  pipenv run flask db upgrade
fi

if [ "$RESET_DB" = "true" ]; then
  echo 'Resetting database and seeding it with example CR Connect data...'
  pipenv run flask load-example-data
fi

if [ "$RESET_DB_RRT" = "true" ]; then
  echo 'Resetting database and seeding it with example RRT data...'
  pipenv run flask load-example-rrt-data
fi

if [ "$APPLICATION_ROOT" = "/" ]; then
  pipenv run gunicorn --bind 0.0.0.0:$PORT0 wsgi:app
else
  pipenv run gunicorn -e SCRIPT_NAME="$APPLICATION_ROOT" --bind 0.0.0.0:$PORT0 wsgi:app
fi

if [ "$FIX_RRT_DATA" = "true" ]; then
  echo 'Fixing RRT data...'
  pipenv run flask rrt-data-fix
fi