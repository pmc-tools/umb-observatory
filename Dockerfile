# Dockerfile for UMB Obervatory
# Based on the Storm docker files.

# Set base image
# We use the storm depencies as a basis as it already includes various necessary packages.
ARG BASE_IMAGE=movesrwth/storm-dependencies:latest


######################################################################
# The final JupyterHub image, platform specific
FROM $BASE_IMAGE AS umbiobservatory
LABEL org.opencontainers.image.authors="pmctools"

ARG TARGETPLATFORM
EXPOSE 8000

# Install dependencies
# For storm: libarchive-dev and ninja-build
# For prism: default-jdk
# For mdoest xz-utils
RUN apt-get update -qq \
 && apt-get install -yqq --no-install-recommends \
    python-is-python3 \
    python3-pip \
    python3-venv \
    unzip  \
 && apt-get install -yqq --no-install-recommends \
    libarchive-dev ninja-build libboost-iostreams-dev \
    default-jdk  \
    xz-utils

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python3 -m pip install  --no-cache-dir  jupyter matplotlib scipy pytest black

#
# CMake build type
ARG storm_build_type=Release
# Specify number of threads to use for parallel compilation
ARG no_threads=1
ARG storm_repo=https://github.com/tquatmann/storm.git
ARG storm_branch=io/binaryformat
ARG prism_repo=https://github.com/prismmodelchecker/prism.git
ARG prism_branch=master

# Build Storm
#############
WORKDIR /opt/

RUN git clone  -b $storm_branch $storm_repo

# Switch to build directory
RUN mkdir -p /opt/storm/build
WORKDIR /opt/storm/build
# Configure Storm
RUN cmake -GNinja -DCMAKE_BUILD_TYPE=$storm_build_type \
          -DSTORM_PORTABLE=ON \
          -DSTORM_USE_LTO=OFF \
          ..
RUN ninja storm-cli -j 4

# Build Prism
#############
WORKDIR /opt/
RUN git clone -b $prism_branch $prism_repo
WORKDIR /opt/prism/prism
RUN make

# Download Modest
#################
WORKDIR /opt/
COPY .docker/install-modest.sh install-modest.sh
RUN bash install-modest.sh

#### Install UMB
RUN python3 -m pip install --no-cache-dir  umbi

#############
RUN mkdir /opt/umb
WORKDIR /opt/umb

# Copy the content of the current local repository into the Docker image
COPY . .
COPY .docker/tools.toml tools.toml

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8000", "--no-browser", "--allow-root"]
