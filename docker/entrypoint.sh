#!/bin/bash
# =================================================================
#
# Author: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

echo "START /entrypoint.sh"

set +e

export NLDI_HOME=/nldi
export NLDI_CONFIG="${NLDI_HOME}/local.source.yml"
export NLDI_OPENAPI="${NLDI_HOME}/local.openapi.yml"

export PYGEOAPI_CONFIG="${NLDI_HOME}/pygeoapi.config.yml"
export PYGEOAPI_OPENAPI="${NLDI_HOME}/pygeoapi.openapi.yml"

# gunicorn env settings with defaults
export SCRIPT_NAME=${NLDI_PATH:=/}
CONTAINER_NAME=${CONTAINER_NAME:=nldi}
CONTAINER_HOST=${CONTAINER_HOST:=0.0.0.0}
CONTAINER_PORT=${CONTAINER_PORT:=80}
WSGI_WORKERS=${WSGI_WORKERS:=4}
WSGI_WORKER_TIMEOUT=${WSGI_WORKER_TIMEOUT:=6000}
WSGI_WORKER_CLASS=${WSGI_WORKER_CLASS:=gevent}

# What to invoke: default is to run gunicorn server
entry_cmd=${1:-run}

# Shorthand
function error() {
        echo "ERROR: $@"
        exit -1
}

# Workdir
cd ${NLDI_HOME}

case ${entry_cmd} in
# Align source table
align)
        nldi config align-sources ${NLDI_CONFIG}
        ;;

# Run NLDI Server
run)
        echo "Trying to generate openapi.yml"
        pygeoapi openapi generate ${PYGEOAPI_CONFIG} --output-file ${PYGEOAPI_OPENAPI}
        nldi openapi generate ${NLDI_CONFIG} --output-file ${NLDI_OPENAPI}

        [[ $? -ne 0 ]] && error "openapi.yml could not be generated ERROR"

        echo "openapi.yml generated continue to nldi"

        # SCRIPT_NAME should not have value '/'
        [[ "${SCRIPT_NAME}" = '/' ]] && export SCRIPT_NAME="" && echo "make SCRIPT_NAME empty from /"

        echo "Start gunicorn name=${CONTAINER_NAME} on ${CONTAINER_HOST}:${CONTAINER_PORT} with ${WSGI_WORKERS} workers and SCRIPT_NAME=${SCRIPT_NAME}"
        exec gunicorn --workers ${WSGI_WORKERS} \
                --worker-class=${WSGI_WORKER_CLASS} \
                --timeout ${WSGI_WORKER_TIMEOUT} \
                --name=${CONTAINER_NAME} \
                --bind ${CONTAINER_HOST}:${CONTAINER_PORT} \
                nldi.flask_app:APP
        ;;

*)
        error "unknown command arg: must be run (default) or align"
        ;;
esac

echo "END /entrypoint.sh"
