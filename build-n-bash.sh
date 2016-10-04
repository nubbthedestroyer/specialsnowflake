#!/usr/bin/env bash

# main block
aws s3 cp s3://ue-itu-secure/params/snowflake/credentials ./infra/scripts/
aws s3 cp s3://ue-itu-secure/params/snowflake/creds.json ./infra/scripts/
docker build -t ss .
rm -rf ./infra/scripts/credentials
rm -rf ./infra/scripts/creds.json
docker run --entrypoint /bin/bash -it ss ${1}