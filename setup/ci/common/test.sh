
#!/bin/bash
set -eux -o pipefail

cur=$(cd $(dirname ${BASH_SOURCE}) && pwd)

# Ensure we're at the root.
test -f WORKSPACE
test -f LICENSE

if [[ $(whoami) != "root" ]]; then
    echo "Should be run under Docker"
    exit 1;
fi

if ! id -u test; then
    useradd -m test
fi

# Run tests.
# We `sudo` into a non-root account so that all workflow tests pass; if we
# were root, then we could nominally overwrite bazel sandbox files.
sudo -u test --set-home bash <<EOF
set -eux -o pipefail
cd ${PWD}
bazel test \
    --announce_rc --curses=no --progress_report_interval 30 \
    //...
EOF
