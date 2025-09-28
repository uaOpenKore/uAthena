# syntax=docker/dockerfile:1
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        clang \
        clang-format \
        clang-tidy \
        cmake \
        pkg-config \
        ccache \
        git \
        zlib1g-dev \
        libpcre3-dev \
        libmariadb-dev \
        libmariadb-dev-compat \
        libssl-dev \
        libreadline-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/uathena
COPY . /opt/uathena

# Use the shared build flags by default and perform a representative build.
RUN make txt

CMD ["/bin/bash"]
