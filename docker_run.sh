#!/bin/bash

# run migrations
export FLASK_APP=./crc/__init__.py

for entry in ./instance/* ; do
  echo "$entry"
  cat $entry
done

if [ "$DOWNGRADE_DB" = "true" ]; then
  echo 'Downgrading...'
  pipenv run flask db downgrade
fi

pipenv run flask db upgrade

if [ "$RESET_DB" = "true" ]; then
  echo 'Resetting database...'
  pipenv run flask load-example-data
fi

pipenv run python ./run.py
