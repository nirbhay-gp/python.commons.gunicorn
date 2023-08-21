#!/bin/sh

(source .env \
    && echo $DOCKER_REPO \
    && REMOTE_IMAGE="${DOCKER_REPO}/gunicorn:${SERVER_VERSION}" \
    && echo $REMOTE_IMAGE \
    && docker tag gunicorn:local $REMOTE_IMAGE\
    && docker push $REMOTE_IMAGE
)