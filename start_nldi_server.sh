#!/bin/sh
# SPDX-License-Identifier: CC0
# See the full copyright notice in LICENSE.md
#
# This script is the entrypoint for the NLDI server container.
set +e

export NLDI_HOME=/nldi
export NLDI_CONFIG="${NLDI_HOME}/local.source.yml"
# export NLDI_OPENAPI="${NLDI_HOME}/local.openapi.yml"

# export PYGEOAPI_CONFIG="${NLDI_HOME}/pygeoapi.config.yml"
# export PYGEOAPI_OPENAPI="${NLDI_HOME}/pygeoapi.openapi.yml"

# gunicorn env settings with defaults
#export SCRIPT_NAME=${NLDI_PATH:=/}
CONTAINER_NAME=${CONTAINER_NAME:=nldi}
CONTAINER_HOST=${CONTAINER_HOST:=0.0.0.0}
CONTAINER_PORT=${CONTAINER_PORT:=80}
WSGI_WORKERS=${WSGI_WORKERS:=4}
WSGI_WORKER_TIMEOUT=${WSGI_WORKER_TIMEOUT:=6000}
WSGI_WORKER_CLASS=${WSGI_WORKER_CLASS:=gevent}

# Shorthand
function error() {
        echo "ERROR: $@"
        exit -1
}

# Workdir
cd ${NLDI_HOME}
exec gunicorn --workers ${WSGI_WORKERS} \
        --worker-class=${WSGI_WORKER_CLASS} \
        --timeout ${WSGI_WORKER_TIMEOUT} \
        --name=${CONTAINER_NAME} \
        --bind ${CONTAINER_HOST}:${CONTAINER_PORT} \
        nldi.server:APP

