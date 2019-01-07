#!/bin/bash
set -eux -o pipefail

cur=$(cd $(dirname ${BASH_SOURCE}) && pwd)

# Ensure we're at the root.
test -f WORKSPACE
test -f LICENSE

# Configure options.
! test -f user.bazelrc
# Ensure we have a specify Python version.
# (Not sure if `which python` will carry through.)
python_bin=$(which python)$(python -c 'import sys; print(sys.version_info.major)')
cat > user.bazelrc <<EOF
build --python_path=${python_bin}
EOF

# Run tests.
bazel test \
    --announce_rc --curses=no --progress_report_interval 30 \
    //...
