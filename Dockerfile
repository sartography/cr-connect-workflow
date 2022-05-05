FROM quay.io/sartography/python:3.8

RUN pip install poetry
RUN useradd _gunicorn --no-create-home --user-group

RUN apt-get update && \
    apt-get install -y -q \
        gcc libssl-dev \
        curl postgresql-client git-core \
        gunicorn3 postgresql-client

WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN cd /app && poetry lock --keep-outdated --requirements > requirements.txt
RUN pip install -r /app/requirements.txt

RUN set -xe \
  && apt-get remove -y gcc python3-dev libssl-dev \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

COPY . /app/
WORKDIR /app
