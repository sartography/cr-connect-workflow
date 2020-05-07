#!/bin/bash

# Build and push Docker image to Docker Hub
echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USERNAME" --password-stdin || exit 1
REPO="sartography/cr-connect-workflow"
TAG=$(if [ "$TRAVIS_BRANCH" == "master" ]; then echo "latest"; else echo "$TRAVIS_BRANCH" ; fi)
docker build -f Dockerfile -t "$REPO:$COMMIT" . || exit 1
docker tag "$REPO:$COMMIT" "$REPO:$TAG" || exit 1
docker tag "$REPO:$COMMIT" "$REPO:travis-$TRAVIS_BUILD_NUMBER" || exit 1
docker push "$REPO" || exit 1

# Wait for Docker Hub
echo "Publishing to Docker Hub..."
sleep 30

# Notify DC/OS that Docker image has been updated
echo "Refreshing DC/OS..."
STAGE=$(if [ "$TRAVIS_BRANCH" == "master" ]; then echo "production"; else echo "$TRAVIS_BRANCH" ; fi)
aws sqs send-message --region "$AWS_DEFAULT_REGION" --queue-url "$AWS_SQS_URL" --message-body "crconnect/$STAGE/backend" || exit 1
