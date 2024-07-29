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

FROM ubuntu:jammy

LABEL maintainer="Benjamin Webb <bwebb@lincolninst.edu>"

# ARG ADD_DEB_PACKAGES="\
#   python3-gdal \
#   python3-psycopg2 \
#   python3-rasterio"

# ENV settings
ENV TZ=${TZ} \
  LANG=${LANG} \
  PIP_NO_CACHE_DIR=1 \
  DEBIAN_FRONTEND="noninteractive" \
  DEB_BUILD_DEPS="\
  curl \
  #gcc \
  unzip" \
  DEB_PACKAGES="\
  locales \
  tzdata \
  python3-psycopg2 \
  python3-pip \
  ${ADD_DEB_PACKAGES}"



# Install operating system dependencies
RUN \
  apt-get update -y \
  && apt-get upgrade -y \
  && apt-get --no-install-recommends install -y ${DEB_PACKAGES} ${DEB_BUILD_DEPS}  \
  # Cleanup
  && apt-get remove --purge -y ${DEB_BUILD_DEPS} \
  && apt-get clean \
  && apt autoremove -y  \
  && rm -rf /var/lib/apt/lists/*

ADD . /nldi
WORKDIR /nldi

RUN \
  pip install --no-deps https://github.com/geopython/pygeoapi/archive/refs/heads/master.zip \
  && pip install -r requirements-docker.txt \
  && pip install -e . \
  # Set default config and entrypoint for Docker Image
  && cp /nldi/docker/default.source.yml /nldi/local.source.yml \
  && cp /nldi/docker/pygeoapi.config.yml /nldi/pygeoapi.config.yml \
  && cp /nldi/docker/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
