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

FROM python:3.11-alpine as build

LABEL maintainer="Benjamin Webb <bwebb@lincolninst.edu>"
LABEL description="Docker image for the NLDI API"
# ENV settings
ENV TZ=${TZ} \
  LANG=${LANG} \
  PIP_NO_CACHE_DIR=1

# Install operating system dependencies
RUN \
  apk update && apk add curl build-base libpq-dev proj-util proj-dev gdal-dev geos-dev

COPY ./requirements-docker.txt ./requirements.txt ./req/


RUN pip install --no-cache-dir -r ./req/requirements.txt
RUN pip install --no-cache-dir -r ./req/requirements-docker.txt



FROM python:3.11-alpine as nldi
RUN apk update && apk add --no-cache gcompat libstdc++ curl proj-util libpq-dev
ADD . /nldi
WORKDIR /nldi
COPY --from=build /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=build /usr/lib/libgdal.so.35 /usr/lib/libgeos.so.3.12.2 /usr/lib/libproj.so.25 /usr/lib/libgeos_c.so.1.18.2 /usr/lib/
COPY --from=build /usr/local/bin/pygeoapi /usr/local/bin/gunicorn /usr/local/bin/

RUN \
  ln -s /usr/lib/libgdal.so.35 /usr/lib/libgdal.so \
  && ln -s /usr/lib/libgeos.so.3.12.2 /usr/lib/libgeos.so \
#  && ln -s /usr/lib/libproj.so.25 /usr/lib/libproj.so \
  && ln -s /usr/lib/libgeos_c.so.1.18.2 /usr/lib/libgeos_c.so.1 \
  && ln -s /usr/lib/libgeos_c.so.1 /usr/lib/libgeos_c.so

RUN pip install -e . \
  && cp /nldi/docker/default.source.yml /nldi/local.source.yml \
  && cp /nldi/docker/pygeoapi.config.yml /nldi/pygeoapi.config.yml \
  && cp /nldi/docker/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
