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

bazel build //bazel_external_data/backends:girder_test
ws=$(bazel info workspace)
${ws}/bazel-bin/bazel_external_data/backends/girder_test ./docker_girder/build/info.yml

# Shutdown.
docker-compose down
