#!/bin/bash

function branch_to_tag () {
  if [ "$1" == "latest" ]; then echo "production"; else echo "$1" ; fi
}

function branch_to_deploy_group() {
  if [[ $1 =~ ^(rrt\/.*)$ ]]; then echo "rrt"; else echo "crconnect" ; fi
}

function branch_to_deploy_stage () {
  if [ "$1" == "master" ]; then echo "production"; else echo "$1" ; fi
}

REPO="sartography/cr-connect-workflow"
TAG=$(branch_to_tag "$TRAVIS_BRANCH")
COMMIT=${TRAVIS_COMMIT::8}

DEPLOY_APP="backend"
DEPLOY_GROUP=$(branch_to_deploy_group "$TRAVIS_BRANCH")
DEPLOY_STAGE=$(branch_to_deploy_stage "$TRAVIS_BRANCH")

if [ "$DEPLOY_GROUP" == "rrt" ]; then
  IFS='/' read -ra ARR <<< "$TRAVIS_BRANCH"  # Split branch on '/' character
  TAG=$(branch_to_tag "rrt_${ARR[1]}")
  DEPLOY_STAGE=$(branch_to_deploy_stage "${ARR[1]}")
fi

DEPLOY_PATH="$DEPLOY_GROUP/$DEPLOY_STAGE/$DEPLOY_APP"
echo "REPO = $REPO"
echo "TAG = $TAG"
echo "COMMIT = $COMMIT"
echo "DEPLOY_PATH = $DEPLOY_PATH"

# Build and push Docker image to Docker Hub
echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USERNAME" --password-stdin || exit 1
docker build -f Dockerfile -t "$REPO:$COMMIT" . || exit 1
docker tag "$REPO:$COMMIT" "$REPO:$TAG" || exit 1
docker tag "$REPO:$COMMIT" "$REPO:travis-$TRAVIS_BUILD_NUMBER" || exit 1
docker push "$REPO" || exit 1

# Wait for Docker Hub
echo "Publishing to Docker Hub..."
sleep 30

# Notify UVA DCOS that Docker image has been updated
echo "Refreshing DC/OS..."
aws sqs send-message --region "$AWS_DEFAULT_REGION" --queue-url "$AWS_SQS_URL" --message-body "$DEPLOY_PATH" || exit 1
