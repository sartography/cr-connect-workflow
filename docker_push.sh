#!/bin/bash

# Build and push Docker image to Docker Hub
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
docker build --no-cache -t sartography/cr-connect-backend:latest . || exit 1;
docker push sartography/cr-connect-backend:latest || exit 1;

# Notify UVA DCOS that Docker image has been updated
aws sqs send-message --queue-url 'https://queue.amazonaws.com/474683445819/dcos-refresh' --message-body 'crconnect/backend' || exit 1;
