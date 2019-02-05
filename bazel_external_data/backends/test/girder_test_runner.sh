#!/bin/bash
set -eux -o pipefail

cd $(dirname $0)

docker_log=/tmp/docker_girder.output.txt

(
    cd docker_girder
    docker-compose build
    echo "docker-compose output: ${docker_log}"
    docker-compose up > ${docker_log} 2>&1 &
    # TODO: Use `wait-for`.
    sleep 5
    # Setup server.
    python setup_server.py
    sleep 5
)

# Setup virtualenv.
(
    rm -rf build/
    mkdir build
    python3 -m virtualenv --python python3 --system-site-packages ./build
    build/bin/python3 -m pip install girder_client
)

bazel build --python_path=${PWD}/build/bin/python3 //bazel_external_data/backends:girder_test
ws=$(bazel info workspace)
${ws}/bazel-bin/bazel_external_data/backends/girder_test ./docker_girder/build/info.yml

# Shutdown.
docker-compose down
