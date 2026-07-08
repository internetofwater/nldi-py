# SPDX-License-Identifier: CC0-1.0
# See the full copyright notice in LICENSE.md

FROM python:3.12-slim-bookworm

LABEL maintainer="Benjamin Webb <bwebb@lincolninst.edu>"
LABEL maintainer="Gene Trantham <gtrantham@usgs.gov>"
LABEL description="Docker image for the NLDI API"

ENV PIP_NO_CACHE_DIR=1

COPY . /nldi
WORKDIR /nldi

RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --prefer-binary --no-cache-dir /nldi

ENTRYPOINT ["/nldi/start_nldi_server.sh"]
