#!/bin/bash

# Build and push Docker image to Docker Hub
echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USERNAME" --password-stdin
REPO="sartography/cr-connect-workflow"
TAG=$(if [ "$TRAVIS_BRANCH" == "master" ]; then echo "latest"; else echo "$TRAVIS_BRANCH" ; fi)
COMMIT=${$TRAVIS_COMMIT::8}
docker build -f Dockerfile -t "$REPO:$COMMIT" .
docker tag "$REPO:$COMMIT" "$REPO:$TAG"
docker tag "$REPO:$COMMIT" "$REPO:travis-$TRAVIS_BUILD_NUMBER"
docker push "$REPO"

# Wait for Docker Hub
echo "Publishing to Docker Hub..."
sleep 30

# Notify DC/OS that Docker image has been updated
echo "Refreshing DC/OS..."
STAGE=$(if [ "$TRAVIS_BRANCH" == "master" ]; then echo "production"; else echo "$TRAVIS_BRANCH" ; fi)
aws sqs send-message --region "$AWS_DEFAULT_REGION" --queue-url "$AWS_SQS_URL" --message-body "crconnect/$STAGE/backend"
