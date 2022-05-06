FROM ghcr.io/sartography/python:3.9

RUN pip install pipenv
RUN useradd _gunicorn --no-create-home --user-group

RUN apt-get update && \
    apt-get install -y -q \
        gcc libssl-dev \
        curl postgresql-client git-core \
        gunicorn3 postgresql-client

WORKDIR /app
COPY Pipfile Pipfile.lock /app/
RUN cd /app && pipenv lock --keep-outdated --requirements > requirements.txt
RUN pip install -r /app/requirements.txt

RUN set -xe \
  && apt-get remove -y gcc python3-dev libssl-dev \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

COPY . /app/
WORKDIR /app
