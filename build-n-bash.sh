#!/usr/bin/env bash

# main block
docker build -t ss .
docker run --entrypoint /bin/bash -it ss ${1}