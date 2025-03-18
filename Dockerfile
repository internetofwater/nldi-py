# SPDX-License-Identifier: CC0
# See the full copyright notice in LICENSE.md
#

FROM python:3.12-alpine AS build
# NOTE: This is a multi-stage build.... the first stage is for building the
# compiled dependencies, which requires gcc and other dev pipeline tools.
# Once those binaries are built, we don't need the build tools anymore, so
# we can copy the compiled binaries to a new image (without dev tooling).
# This keeps the final image smaller and more secure.

LABEL maintainer="Benjamin Webb <bwebb@lincolninst.edu>"
LABEL description="Docker image for the NLDI API"
# ENV settings
# ENV TZ=${TZ} \

ENV \
  LANG=${LANG} \
  PIP_NO_CACHE_DIR=1

COPY ./docker/DOICert.crt /usr/local/share/ca-certificates/DOICert.crt
RUN chmod 644 /usr/local/share/ca-certificates/*.crt && update-ca-certificates
RUN \
  apk update && \
  apk add --no-cache curl build-base libpq-dev geos-dev gdal-dev proj-dev proj-util


ADD . /nldi
WORKDIR /nldi

#RUN pip install --prefer-binary --trusted-host pypi.org --trusted-host files.pythonhosted.org --no-cache-dir .  && rm -rf /root/.cache/pip
RUN pip install --prefer-binary --no-cache-dir .  && rm -rf /root/.cache/pip


# This will be the final image:
FROM python:3.12-alpine AS nldi
ADD . /nldi
WORKDIR /nldi
COPY --from=build /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=build /usr/local/bin/gunicorn /usr/local/bin/
COPY --from=build /usr/lib/libpq.so.5 /usr/lib/
RUN mv /nldi/tests/data/nldi_server_config.yml /nldi/local.source.yml

ENTRYPOINT ["/nldi/start_nldi_server.sh"]
