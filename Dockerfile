# SPDX-License-Identifier: CC0
# See the full copyright notice in LICENSE.md
#

FROM python:3.12-alpine AS build
# NOTE: This is a multi-stage build.... the first stage is for building the compiled dependencies, which requires gcc and other build tools.
# Once those binaries are built, we don't need the build tools anymore, so we can copy the compiled binaries to a new image that doesn't have them.
# This keeps the final image smaller and more secure.

LABEL maintainer="Benjamin Webb <bwebb@lincolninst.edu>"
LABEL description="Docker image for the NLDI API"
# ENV settings
# ENV TZ=${TZ} \

ENV LANG=${LANG} \
  PIP_NO_CACHE_DIR=1

# Install operating system dependencies
RUN \
  apk update && \
  apk add --no-cache curl build-base libpq-dev

ADD . /nldi
WORKDIR /nldi

RUN pip install --no-cache-dir . \
    && rm -rf /root/.cache/pip


# This will be the final image:
FROM python:3.12-alpine AS nldi
ADD . /nldi
WORKDIR /nldi
COPY --from=build /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=build /usr/local/bin/gunicorn /usr/local/bin/
COPY --from=build /usr/lib/libpq.so.5 /usr/lib/

# RUN cp /nldi/docker/default.source.yml /nldi/local.source.yml \
#     && cp /nldi/docker/pygeoapi.config.yml /nldi/pygeoapi.config.yml \
#     && cp /nldi/docker/entrypoint.sh /entrypoint.sh

# ENTRYPOINT ["/entrypoint.sh"]
