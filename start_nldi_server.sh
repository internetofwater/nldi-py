#!/bin/sh
# SPDX-License-Identifier: CC0-1.0
# See the full copyright notice in LICENSE.md
#
# This script is the entrypoint for the NLDI server container.
set +e

export NLDI_HOME=/nldi
export NLDI_CONFIG="${NLDI_HOME}/local.source.yml"

#export SCRIPT_NAME=${NLDI_PATH:=/}
CONTAINER_NAME=${CONTAINER_NAME:=nldi}
CONTAINER_HOST=${CONTAINER_HOST:=0.0.0.0}
CONTAINER_PORT=${CONTAINER_PORT:=8080}
WSGI_WORKERS=${WSGI_WORKERS:=4}
WSGI_WORKER_TIMEOUT=${WSGI_WORKER_TIMEOUT:=120}

# Workdir
cd ${NLDI_HOME}
echo "name=${CONTAINER_NAME} ; bind=${CONTAINER_HOST}:${CONTAINER_PORT}"
exec hypercorn -w ${WSGI_WORKERS} \
        --bind ${CONTAINER_HOST}:${CONTAINER_PORT} \
        --workers ${WSGI_WORKERS} \
        --log-level DEBUG \
        --keepalive 600 \
        nldi.asgi:APP

# Keepalive set high -- to prevent hypercorn giving up on a long-running request by the worker. 
