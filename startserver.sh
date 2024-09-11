

export NLDI_PATH=/api/nldi
export NLDI_URL=http://localhost:8081/api/nldi
export NLDI_DB_HOST=172.17.0.2
export NLDI_DB_PORT=5432
export NLDI_DB_NAME=nldi
export NLDI_DB_USERNAME=nldi
export NLDI_DB_PASSWORD=changeMe
export PYGEOAPI_URL=https://labs.waterdata.usgs.gov/api/nldi/pygeoapi/

export NLDI_HOME=./tests/data
export NLDI_CONFIG="${NLDI_HOME}/sources_config.yml"
export NLDI_OPENAPI="${NLDI_HOME}/local.openapi.yml"

# nldi openapi generate ${NLDI_CONFIG} --output-file ${NLDI_OPENAPI}
#nldi openapi generate ${NLDI_CONFIG} --output-file /tmp/openapi_local.json --format json
# gunicorn --bind localhost:8081 nldi.flask_app:APP
gunicorn --bind localhost:8081 nldi.server:APP --reload
