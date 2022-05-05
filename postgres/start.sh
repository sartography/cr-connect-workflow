#!/usr/bin/env bash

function error_handler() {
  >&2 echo "Exited with BAD EXIT CODE '${2}' in ${0} script at line: ${1}."
  exit "$2"
}
trap 'error_handler ${LINENO} $?' ERR
set -o errtrace -o errexit -o nounset -o pipefail

docker stop postgres_db_1 || echo ''
mkdir -p "${HOME}/docker/volumes/postgres"

if command -v docker-compose >/dev/null ; then
  docker-compose -f postgres/docker-compose.yml up --no-start
  docker-compose -f postgres/docker-compose.yml start
else
  docker compose -f postgres/docker-compose.yml up --no-start
  docker compose -f postgres/docker-compose.yml start
fi
