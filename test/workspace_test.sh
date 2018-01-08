#!/bin/bash
set -e -u

# Copy necessary files to create a (set of) workspace(s) from an existing Bazel
# workspace. For meta-testing Bazel workflows.

# Prevent from running outside of Bazel.
if [[ ! $(basename $(dirname ${PWD})) =~ .*\.runfiles ]]; then
    echo "Must be run from within Bazel"
    exit 1
fi

cmd=${1}
pkg_reldir=${2}
shift && shift
extra_dirs="$@"

tmp_base=/tmp/bazel_workspace_test
mkdir -p ${tmp_base}
export WORKSPACE_TMP=$(mktemp -d -p ${tmp_base})

# Copy what's needed for a modifiable `bazel_pkg_advanced_test` directory.
mock_dir=${WORKSPACE_TMP}/mock_workspace

srcs="${pkg_reldir} ${extra_dirs}"
mkdir -p ${mock_dir}
readlink-py() { python -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' ${1}; }
for src in ${srcs}; do
    subdir=$(dirname ${src})
    mkdir -p ${mock_dir}/${subdir}
    cp -r $(readlink-py ${src}) ${mock_dir}/${subdir}
done

# Change to the workspace directory, and begin.
cd ${mock_dir}/${pkg_reldir}
# Get rid of Bazel symlinks.
rm bazel-* || :
# Execute command.
eval ${cmd}
