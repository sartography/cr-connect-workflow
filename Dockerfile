FROM python:3.7-slim

WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN pip install pipenv && \
  apt-get update && \
  apt-get install -y --no-install-recommends \
    gcc python3-dev libssl-dev postgresql-client git-core && \
  pipenv install --deploy --system && \
  apt-get remove -y gcc python3-dev libssl-dev && \
  apt-get purge -y --auto-remove && \
  rm -rf /var/lib/apt/lists/ *

COPY app ./

ENV FLASK_APP=./crc/__init__.py
CMD ["pipenv", "run", "python", "./run.py"]

# expose ports
EXPOSE 5000
