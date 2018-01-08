#!/bin/bash

cd $(dirname ${0})

# `bazel test ...` does not like having workspace sym-links, as it starts
# chaining them.
find . -type l -name 'bazel-*' | xargs rm
