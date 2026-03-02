# SPDX-License-Identifier: CC0-1.0
# See the full copyright notice in LICENSE.md
#

FROM python:3.12-slim-bookworm

LABEL maintainer="Benjamin Webb <bwebb@lincolninst.edu>"
LABEL maintainer="Gene Trantham <gtrantham@usgs.gov>"
LABEL description="Docker image for the NLDI API"
# ENV settings
# ENV TZ=${TZ} \

ENV \
  LANG=${LANG} \
  PIP_NO_CACHE_DIR=1


ADD . /nldi
WORKDIR /nldi

RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --prefer-binary --no-cache-dir /nldi  && rm -rf /root/.cache/pip

RUN mv /nldi/tests/data/nldi_server_config.yml /nldi/local.source.yml

ENTRYPOINT ["/nldi/start_nldi_server.sh"]
