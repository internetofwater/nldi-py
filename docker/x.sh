#!/bin/sh

export NLDI_PATH=/api/nldi
export NLDI_URL=http://localhost:8080/
export NLDI_DB_HOST=nldi-db
export NLDI_DB_PORT=5432
export NLDI_DB_NAME=nldi
export NLDI_DB_USERNAME=nldi
export NLDI_DB_PASSWORD=changeMe
export PYGEOAPI_URL=https://labs.waterdata.usgs.gov/api/nldi/pygeoapi/

hypercorn -w 2 --read-timeout 6000 --bind 0.0.0.0:8001 nldi.asgi:APP
