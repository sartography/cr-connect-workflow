FROM python:3.7-slim

WORKDIR /app
COPY Pipfile Pipfile.lock /app/

RUN set -xe \
  && pip install pipenv \
  && apt-get update -q \
  && apt-get install -y -q \
        gcc python3-dev libssl-dev \
        curl postgresql-client git-core \
        gunicorn3 postgresql-client \
  && pipenv install --dev \
  && apt-get remove -y gcc python3-dev libssl-dev \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/* \
  && mkdir -p /app \
  && useradd _gunicorn --no-create-home --user-group

COPY . /app/
WORKDIR /app
