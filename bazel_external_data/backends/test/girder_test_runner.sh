#!/bin/bash
set -eux -o pipefail

cd $(dirname $0)

(
    cd docker_girder
    docker-compose build
    docker-compose rm -fs  # Yuck.
    docker-compose up --force-recreate --abort-on-container-exit &
    # TODO: Use `wait-for`.
    sleep 5
    # Setup server.
    python setup_server.py
    sleep 5
)

bazel build //bazel_external_data/backends:girder_test
ws=$(bazel info workspace)
${ws}/bazel-bin/bazel_external_data/backends/girder_test ./docker_girder/build/info.yml

echo "[ Success ]"
(
    cd docker_girder
    docker-compose stop
)
