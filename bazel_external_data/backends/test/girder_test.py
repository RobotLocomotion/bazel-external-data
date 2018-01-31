"""
Provides a simple test script for uploading and download a file.

If testing against Drake Girder, create somthing like `/tmp/drake_girder.yml`
with these contents:

```
url: https://drake-girder.csail.mit.edu
folder_path: /collection/test/files
api_key: <copy API key here>
```

Then call this script with this file:

    $ bazel run :girder_test -- /tmp/drake_girder.yml

"""

import argparse
import datetime
import os
import sys
import time
import yaml

from bazel_external_data import core, hashes
from bazel_external_data.backends.girder import GirderHashsumBackend

parser = argparse.ArgumentParser()
parser.add_argument("config_file", type=str)
parser.add_argument("--num_downloads", type=int, default=1)
args = parser.parse_args()

with open(args.config_file) as f:
    config = yaml.load(f)

url = config["url"]
folder_path = config["folder_path"]
api_key = config["api_key"]

project_root = "/tmp/bazel_external_data/root"
output = "/tmp/bazel_external_data/output"

user_config = core.USER_CONFIG_DEFAULT
user_config.update(yaml.load("""
girder:
  url:
    "{url}":
        api_key: {api_key}
""".format(url=url, api_key=api_key)))
user = core.User(user_config)

config = yaml.load("""
backend: girder_hashsum
url: {url}
folder_path: {folder_path}
""".format(url=url, folder_path=folder_path))

backend = GirderHashsumBackend(config, project_root, user)

relpath = "test.txt"
path = os.path.join(project_root, relpath)

if not os.path.exists(project_root):
    os.makedirs(project_root)
if not os.path.exists(output):
    os.makedirs(output)
with open(path, 'w') as f:
    f.write("Test file: " + str(datetime.datetime.now()))

hash = hashes.sha512.compute(path)
if not backend.check_file(hash, relpath):
    backend.upload_file(hash, relpath, path)
time.sleep(1)
for i in range(args.num_downloads):
    print("Download: {}".format(i))
    output_path = os.path.join(output, relpath)
    if os.path.exists(output_path):
        os.unlink(output_path)
    backend.download_file(hash, relpath, output_path)
    hash.compare_file(output_path, do_throw=True)
    sys.stdout.flush()
