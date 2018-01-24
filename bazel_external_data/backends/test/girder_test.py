#!/usr/bin/env python

"""
Provides a simple test script for uploading and download a file.
"""

import os
import yaml

from bazel_external_data import core, util, hashes, config_helpers
from bazel_external_data.backends.girder import GirderHashsumBackend

import argparse

assert not util.in_bazel_runfiles()

parser = argparse.ArgumentParser()
parser.add_argument("--url", type=str, default="https://drake-girder.csail.mit.edu")
parser.add_argument("--folder_path", type=str, default="/collection/test/files")
parser.add_argument("api_key", type=str)
args = parser.parse_args()

project_root = "/tmp/bazel_external_data/root"
output = "/tmp/bazel_external_data/output"

assert args.api_key is not None

user_config = core.USER_CONFIG_DEFAULT
user_config.update(yaml.load("""
girder:
  url:
    "{url}":
        api_key: {api_key}
""".format(url=args.url, api_key=args.api_key)))
user = core.User(user_config)

config = yaml.load("""
backend: girder_hashsum
url: {url}
folder_path: {folder_path}
""".format(url=args.url, folder_path=args.folder_path))

backend = GirderHashsumBackend(config, project_root, user)

relpath = "test.txt"
path = os.path.join(project_root, relpath)

hash = hashes.sha512.compute(path)
if not backend.check_file(hash, relpath):
    backend.upload_file(hash, relpath, path)
backend.download_file(hash, relpath, os.path.join(output, relpath))
