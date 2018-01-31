#!/usr/bin/env python

import sys
import json
from base64 import b64encode
import time
import requests
import yaml
import argparse
import os
import subprocess

def subshell(cmd):
    subprocess.check_call(cmd, shell=True)

parser = argparse.ArgumentParser()
parser.add_argument("--url", type=str, default="http://localhost:8080")
parser.add_argument("--auth", type=str, default="admin:password")
parser.add_argument("--container", type=str, default="dockergirder_girder_1")

args = parser.parse_args()

# See notes in `Dockerfile`.
d = dict(container=args.container)
subshell("docker exec {container} bash -c 'python /girder/tests/setup_database.py /tmp/setup_server.yml'".format(**d))

url = args.url
auth = b64encode(args.auth)
api_url = url + "/api/v1"
token = None

def action(endpoint, params={}, headers=None, method="get", **kwargs):
    def json_value(value):
        if isinstance(value, str):
            return value
        else:
            return json.dumps(value)
    headers = headers and dict(headers) or {}
    if token:
        headers.update({"Girder-Token": token})
    params = {key: json_value(value) for key, value in params.iteritems()}
    func = getattr(requests, method)
    r = func(api_url + endpoint, params=params, headers=headers)
    r.raise_for_status()
    return r.json()

# Auhtorize and generate API key.
response = action("/user/authentication", headers = {"Authorization": "Basic {}".format(auth)})
token = response['authToken']['token']
api_key = action("/api_key", params={"active": True}, method="post")['key']

# Check plugins on the server.
plugins = action("/system/plugins")
my_plugin = "hashsum_download"
if my_plugin not in plugins["all"]:
    raise RuntimeError("Plugin must be installed: {}".format(my_plugin))
enabled = plugins["enabled"]
if my_plugin not in enabled:
    enabled.append(my_plugin)
    print("Enable: {}".format(enabled))
    response = action("/system/plugins", {"plugins": json.dumps(enabled)}, method="put")
    print("Rebuilding...")
    action("/system/web_build", method="post")
    print("Restarting...")
    action("/system/restart", method = "put")
    time.sleep(1)
    print("[ Done ]")

# Generate the user config.
# To be run by `setup_client.sh`.
cur_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(cur_dir)
if not os.path.exists("build"):
    os.makedirs("build")
output_file = "build/info.yml"

with open(output_file, 'w') as f:
    f.write(yaml.dump({
        "url": url,
        "folder_path": "/collection/test/files",
        "api_key": str(api_key),
    }, default_flow_style=False))

print("api_key: {}".format(api_key))
