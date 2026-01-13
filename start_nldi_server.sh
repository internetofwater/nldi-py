#!/bin/sh
# SPDX-License-Identifier: CC0-1.0
# See the full copyright notice in LICENSE.md
#
# This script is the entrypoint for the NLDI server container.
set +e

export NLDI_HOME=/nldi
export NLDI_CONFIG="${NLDI_HOME}/local.source.yml"


# gunicorn env settings with defaults
#export SCRIPT_NAME=${NLDI_PATH:=/}
CONTAINER_NAME=${CONTAINER_NAME:=nldi}
CONTAINER_HOST=${CONTAINER_HOST:=0.0.0.0}
CONTAINER_PORT=${CONTAINER_PORT:=8080}
WSGI_WORKERS=${WSGI_WORKERS:=4}                    # https://docs.gunicorn.org/en/stable/settings.html#workers
WSGI_WORKER_TIMEOUT=${WSGI_WORKER_TIMEOUT:=120}    # https://docs.gunicorn.org/en/stable/settings.html#timeout


# Workdir
cd ${NLDI_HOME}
echo "name=${CONTAINER_NAME} ; bind=${CONTAINER_HOST}:${CONTAINER_PORT}"
exec gunicorn -w ${WSGI_WORKERS} \
        --bind ${CONTAINER_HOST}:${CONTAINER_PORT} \
        --timeout ${WSGI_WORKER_TIMEOUT} \
        -k uvicorn.workers.UvicornWorker \
        nldi.asgi:APP \
        --worker-connections 100  ## Per https://docs.gunicorn.org/en/stable/settings.html#worker-class, this has no effect on custom worker classes.
