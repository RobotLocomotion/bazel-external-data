from datetime import datetime
import json
import os

import requests
import yaml

from bazel_external_data import util
from bazel_external_data.core import Backend


class S3Backend(Backend):
    """Supports a minimal store located in an s3 bucket with access gated by
    an API key."""
    def __init__(self, config, project_root, user):
        Backend.__init__(self, config, project_root, user)
        self._name = "s3"
        self._disable_upload = config.get('disable_upload', False)
        self._verbose = config.get('verbose', False)
        self._url = config['url']

        # Get (optional) authentication information.
        url_config_node = util.get_chain(
            user.config, [self._name, 'url', self._url])
        self._api_key = util.get_chain(url_config_node, ['api_key'])

    def _send_request(self, request_type, path, data=None):
        headers = {'Authorization': self._api_key}
        if self._verbose:
            print(f"request {request_type} {path}")
            print(f"with headers {headers}")
        if request_type == 'PUT':
            return requests.put(self._url + path, data=data, headers=headers)
        elif request_type == 'GET':
            return requests.get(self._url + path, headers=headers)
        elif request_type == 'HEAD':
            return requests.head(self._url + path, headers=headers)
        else:
            raise RuntimeError(f"Invalid operation {request_type}.")

    def check_file(self, hash, _project_relpath):
        path = f"{hash.get_algo()}/{hash.get_value()}"
        response = self._send_request('HEAD', path)
        assert (response.status_code in {200, 400, 403}), response.status_code
        return response.status_code == 200

    def download_file(self, hash, project_relpath, output_file):
        if not self.check_file(hash, project_relpath):
            raise util.DownloadError(
                f"File not available '{project_relpath}"
                f" (hash: {hash.get_value()})")
        path = f"{hash.get_algo()}/{hash.get_value()}"
        response = self._send_request('GET', path)
        if response.status_code == 200:
            with open(output_file, 'wb') as file:
                file.write(response.content)
            print("File downloaded successfully!")
        else:
            print("Failed to download file. "
                  f"Status code: {response.status_code}")

    def upload_file(self, hash, project_relpath, file_path):
        if self._disable_upload:
            raise RuntimeError("Upload disabled")
        with open(file_path, 'rb') as file:
            path = f"{hash.get_algo()}/{hash.get_value()}"
            response = self._send_request('PUT', path, data=file)
            if response.status_code == 200:
                print("File uploaded successfully!")
            else:
                print("Failed to upload file. Status code:",
                      response.status_code)
                print(response.headers)
                print(response.text)
