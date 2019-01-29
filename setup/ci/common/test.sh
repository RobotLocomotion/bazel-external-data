#!/bin/bash
set -eux -o pipefail

cur=$(cd $(dirname ${BASH_SOURCE}) && pwd)

# Ensure we're at the root.
test -f WORKSPACE
test -f LICENSE

# Configure options.
! test -f user.bazelrc
cat > user.bazelrc <<EOF
import %workspace%/setup/ci/common/bazel.rc
EOF

# Run tests.
bazel test //...
