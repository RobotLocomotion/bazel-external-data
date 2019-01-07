#!/bin/bash
set -eux -o pipefail

# Ensure this is only run with `TEST_TMPDIR` present (called from
# `workspace_test.sh`).
[[ -n "${TEST_TMPDIR}" ]]

package_relpath="${1}"
shift

# Create mock drake/WORKSPACE file.
! test -f ./WORKSPACE
echo 'workspace(name = "drake")' > ./WORKSPACE
# Record directory.
drake_dir="${PWD}"

# Ensure that temporary directories are remapped
find . -name '*external_data.*' | \
    xargs sed -i "s#/tmp/bazel_external_data#${TEST_TMPDIR}#g"

# Default to Python 3.
if [[ ! -f user.bazelrc ]]; then
    cat > user.bazelrc <<EOF
build --python_path=/usr/bin/python3
EOF
fi
cp user.bazelrc ${package_relpath}/user.bazelrc

# Change to the workspace directory.
cd "${package_relpath}"
# Ensure path to Drake is corrected.
echo "def get_drake_path(_): return \"${drake_dir}\"" > ./drake_path.bzl
# Get rid of Bazel symlinks if they already exist.
rm bazel-* 2> /dev/null || :

# Run command.
cat user.bazelrc
exec "$@"
