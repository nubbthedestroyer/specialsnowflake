#!/usr/bin/env bash

# decide what flake to run
if [ -z ${1} ]; then
    flake="example-hourly"
else
    flake="${1}"
fi

# main block
cp ~/.aws/credentials .
docker build -t ss . && docker run ss ${flake}
rm credentials