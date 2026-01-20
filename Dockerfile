# Dockerfile for Storm
######################
# The Docker image can be built by executing:
# docker build -t yourusername/storm .
# A different base image can be set from the commandline with:
# --build-arg BASE_IMAGE=<new_base_image>
# Dockerfile installing all dependencies for Storm
##################################################
# The Docker image can be built by executing:
# docker build -t yourusername/storm-dependencies .
# A different base image can be set from the commandline with:
# --build-arg BASE_IMAGE=<new_base_image>

# Set base image
ARG BASE_IMAGE=movesrwth/storm-dependencies:latest
ARG TARGETPLATFORM

######################################################################
# The final JupyterHub image, platform specific
FROM $BASE_IMAGE AS umbihub
LABEL org.opencontainers.image.authors="dev@stormchecker.org"

EXPOSE 8000

RUN apt-get update -qq \
 && apt-get install -yqq --no-install-recommends \
    python-is-python3 \
    python3-pip \
    python3-venv

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python3 -m pip install  --no-cache-dir  jupyter matplotlib scipy pytest black

#
# CMake build type
ARG storm_build_type=Release
# Specify number of threads to use for parallel compilation
ARG no_threads=1
#
# For storm: libarchive-dev and ninja-build
# For prism: default-jdk
RUN apt-get update -qq \
 && apt-get install -yqq --no-install-recommends \
    libarchive-dev ninja-build libboost-iostreams-dev \
    default-jdk

# Build Storm
#############
WORKDIR /opt/

RUN git clone  -b io/binaryformat https://github.com/tquatmann/storm.git

# Switch to build directory
RUN mkdir -p /opt/storm/build
WORKDIR /opt/storm/build

# Configure Storm
RUN cmake -GNinja -DCMAKE_BUILD_TYPE=$storm_build_type \
          -DSTORM_PORTABLE=ON \
          -DSTORM_USE_LTO=OFF \
          ..
RUN ninja storm-cli -j 4

WORKDIR /opt/

RUN git clone -b umb https://github.com/davexparker/prism.git
WORKDIR /opt/prism/prism
RUN make

#### Install UMB
RUN python3 -m pip install --no-cache-dir  umbi

#############
RUN mkdir /opt/umb
WORKDIR /opt/umb

# Copy the content of the current local repository into the Docker image
COPY . .
COPY .docker/tools.toml tools.toml

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8000", "--no-browser", "--allow-root"]
