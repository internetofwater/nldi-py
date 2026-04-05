#!/bin/sh
# SPDX-License-Identifier: CC0-1.0
# See the full copyright notice in LICENSE.md
#
# Entrypoint for the NLDI server container.
set +e

CONTAINER_HOST=${CONTAINER_HOST:=0.0.0.0}
CONTAINER_PORT=${CONTAINER_PORT:=8080}
WSGI_WORKERS=${WSGI_WORKERS:=4}

echo "bind=${CONTAINER_HOST}:${CONTAINER_PORT} workers=${WSGI_WORKERS}"
exec uvicorn \
        --host ${CONTAINER_HOST} \
        --port ${CONTAINER_PORT} \
        --workers ${WSGI_WORKERS} \
        nldi.asgi:app
