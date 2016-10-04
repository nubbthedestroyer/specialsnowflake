#!/usr/bin/env bash

set +e

docker rmi $(docker images -a --filter=dangling=true -q)
docker rm $(docker ps --filter=status=exited --filter=status=created -q)
docker kill $(docker ps -q)
docker_clean_ps
docker rmi $(docker images -a -q)