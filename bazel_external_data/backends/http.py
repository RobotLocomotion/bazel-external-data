from datetime import datetime
import json
import os
import time

import requests
import yaml

from bazel_external_data import util
from bazel_external_data.core import Backend


class HttpBackend(Backend):
    """An Http PUT/GET server (like S3) with access gated by an API key.

    This is the simplest possible remote content-addressable cache; files are
    stored and retrieved by digests of their content without any further
    processing.  Some minimal metadata is stored for debugging purposes only.

    In practice an HTTP store used in this way should always be hidden behind
    a proxy such as cloudfront to enforce authentication and to avoid exposing
    too many details to the world.
    """
    def __init__(self, config, project_root, user):
        Backend.__init__(self, config, project_root, user)
        self._name = "http"
        self._disable_upload = config.get('disable_upload', False)
        self._verbose = config.get('verbose', False)
        self._url = config['url']
        self._path_prefix = config['folder_path']

        # Let python `requests` handle retry logic for us if Http gives us
        # backpressure (503) or on other less common server errors.
        self._http = requests.Session()
        retries = requests.adapters.Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[ 500, 502, 503, 504 ])
        self._http.mount('https://',
                         requests.adapters.HTTPAdapter(max_retries=retries))

        # Get (optional) authentication information.
        url_config_node = util.get_chain(
            user.config, [self._name, 'url', self._url])
        self._api_key = util.get_chain(url_config_node, ['api_key'])

    def _send_request(self, request_type, path, data=None,
                      extra_headers=None):
        headers = (extra_headers or {}) | {'Authorization': self._api_key}
        if self._verbose:
            print(f"request {request_type} {path}")
            print(f"with headers {headers}")
        if request_type == 'PUT':
            return self._http.put(self._url + path, data=data, headers=headers)
        elif request_type == 'GET':
            return self._http.get(self._url + path, headers=headers)
        elif request_type == 'HEAD':
            return self._http.head(self._url + path, headers=headers)
        else:
            raise RuntimeError(f"Invalid operation {request_type}.")

    def _object_path(self, hash):
        hash_path = ("" if hash.get_algo() == "sha512"
                     else f"{hash.get_value()}/")
        return f"{self._path_prefix}{hash_path}/{hash.get_value()}"

    def check_file(self, hash, _project_relpath):
        path = self._object_path(hash)
        response = self._send_request('HEAD', path)
        assert response.status_code in {200, 400, 403, 404}
        return response.status_code == 200

    def download_file(self, hash, project_relpath, output_file):
        if not self.check_file(hash, project_relpath):
            raise util.DownloadError(
                f"File not available '{project_relpath}"
                f" (hash: {hash.get_value()})")
        path = self._object_path(hash)
        response = self._send_request('GET', path)
        if response.status_code == 200:
            with open(output_file, 'wb') as file:
                file.write(response.content)
            print("File downloaded successfully!")
        else:
            print("Failed to download file. "
                  f"Status code: {response.status_code}")

    def upload_file(self, hash, project_relpath, filepath):
        if self._disable_upload:
            raise RuntimeError("Upload disabled")
        with open(filepath, 'rb') as file:
            path = self._object_path(hash)
            response = self._send_request(
                'PUT', path, data=file,
                # These extra headers have no effect on the backend but
                # can aid in analysis and debugging by preserving some of the
                # data used in the girder backend.
                extra_headers={
                    'x-amz-meta-original-path': project_relpath,
                    'x-amz-meta-original-name': os.path.basename(filepath),
                    'x-amz-meta-original-time': datetime.utcnow().isoformat(),
                })
            if response.status_code in (200, 201):
                print("File uploaded successfully!")
            else:
                print("Failed to upload file. Status code:",
                      response.status_code)
                print(response.headers)
                print(response.text)
