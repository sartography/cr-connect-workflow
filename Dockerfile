FROM python:3.7-slim

WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN pip install pipenv && \
  apt-get update && \
  apt-get -y install --no-install-recommends gcc python3-dev libssl-dev postgresql-client && \
  pipenv install --deploy --system && \
  apt-get remove -y gcc python3-dev libssl-dev && \
  apt-get autoremove -y

COPY app ./

ENV FLASK_APP=./crc/__init__.py
CMD ["pipenv", "run", "python", "./run.py"]

# expose ports
EXPOSE 5000
