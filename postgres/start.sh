#!/bin/bash

docker stop postgres_db_1
mkdir -p $HOME/docker/volumes/postgres
#docker pull postgres:latest
#docker run --rm   --name pg-docker -e POSTGRES_PASSWORD=docker -d -p 5432:5432 -v $HOME/docker/volumes/postgres:/var/lib/postgresql/data  postgres
docker-compose -f docker-compose.yml up --no-start
docker-compose -f docker-compose.yml start
