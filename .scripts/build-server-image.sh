#!/bin/sh

pipenv requirements > requirements.txt
docker build --platform linux/amd64 -f .docker/Dockerfile.Server -t junio/gunicorn:local .