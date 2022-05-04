#!/usr/bin/env bash

function error_handler() {
  >&2 echo "Exited with BAD EXIT CODE '${2}' in ${0} script at line: ${1}."
  exit "$2"
}
trap 'error_handler ${LINENO} $?' ERR
set -o errtrace -o errexit -o nounset -o pipefail

docker stop postgres_db_1 || echo ''
mkdir -p "${HOME}/docker/volumes/postgres"

#docker pull postgres:latest
#docker run --rm   --name pg-docker -e POSTGRES_PASSWORD=docker -d -p 5432:5432 -v $HOME/docker/volumes/postgres:/var/lib/postgresql/data  postgres

if command -v docker-compose >/dev/null ; then
  docker-compose -f docker-compose.yml up --no-start
  docker-compose -f docker-compose.yml start
else
  docker compose -f postgres/docker-compose.yml up --no-start
  docker compose -f postgres/docker-compose.yml start
fi
