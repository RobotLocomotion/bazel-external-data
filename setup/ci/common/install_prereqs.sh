#!/bin/bash
set -eux -o pipefail

# WARNING: This should only be run for CI.

echo 'APT::Acquire::Retries "4";' > /etc/apt/apt.conf.d/80-acquire-retries
echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/90-get-assume-yes
export DEBIAN_FRONTEND='noninteractive'

./setup/ubuntu/deb_install

python3 -m pip install -r ./setup/pip_requirements.txt
