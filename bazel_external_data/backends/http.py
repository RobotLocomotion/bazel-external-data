from datetime import datetime
import os
import time

import requests
import yaml

from bazel_external_data import util
from bazel_external_data.core import Backend


class HttpBackend(Backend):
    """An HTTP PUT/GET server (like S3) with access gated by an API key.

    This is the simplest possible remote content-addressable cache; files are
    stored and retrieved by digests of their content without any further
    processing.  Some minimal metadata is stored for debugging purposes only.

    In practice an HTTP store used in this way should always be hidden behind
    a proxy such as cloudfront to enforce authentication and to avoid exposing
    too many details to the world.

    Note that unlike other backends, this backend allows the API key to be
    stored in the repository configuration.  This may or may not be desirable
    depending on your repository's security configuration.  Storing the API
    key in the user configuration is still supported.
    """
    def __init__(self, config, project_root, user):
        Backend.__init__(self, config, project_root, user)
        self._name = "http"
        self._disable_upload = config.get('disable_upload', False)
        self._verbose = config.get('verbose', False)
        self._url = config['url']
        self._path_prefix = config['folder_path']

        self._http = requests.Session()

        # Get (optional) authentication information.
        if self._name in user.config:
            url_config_node = util.get_chain(
                user.config, [self._name, 'url', self._url])
            self._api_key = util.get_chain(url_config_node, ['api_key'])
        else:
            self._api_key = config['api_key']

    def _verbose_print(self, text):
        if self._verbose:
            print(text)

    def _send_request_once(self, request_type, path, data=None,
                           extra_headers=None):
        headers = (extra_headers or {}) | {'Authorization': self._api_key}
        self._verbose_print(f"request {request_type} {path}")
        self._verbose_print(f"with headers {headers}")
        if request_type == 'PUT':
            result = self._http.put(self._url + path,
                                    data=data, headers=headers)
        elif request_type == 'GET':
            result = self._http.get(self._url + path, headers=headers)
        elif request_type == 'HEAD':
            result = self._http.head(self._url + path, headers=headers)
        else:
            raise RuntimeError(f"Invalid operation {request_type}.")
        return result

    def _send_request(self, request_type, path, data=None,
                      extra_headers=None):
        # Naively one would use `requests.adapters.HTTPAdapter`'s retry
        # feature, but the underlying urllib call discards the failed
        # requests which makes debugging impossible.
        #
        # This logic was put in place to debug a complicated failure of
        # layered timeouts and should not be simplified without great care.
        retry_statuses = {500, 502, 503, 504}

        # Sometimes retrying queries within the same session doesn't help, so
        # we also allow one retry of the whole session if all else fails.
        session_retries = 3
        response = None
        while session_retries >= 0:
            # Try `retries` many times, starting with a delay of `delay` and
            # increasing it by `backoff_multiplier` with each failure.
            retries = 11
            delay = 0.2
            backoff_multiplier = 1.8
            # Max delay: delay * multiplier ** (retries - 1)
            while retries >= 0:
                response = self._send_request_once(
                    request_type, path, data, extra_headers)
                if response.status_code not in retry_statuses:
                    return response  # Success or irrecoverable failure.
                if retries > 0:
                    self._verbose_print(
                        f"Retrying after {response.status_code}; "
                        f"{retries} tries remain.")
                    time.sleep(delay)
                    delay *= backoff_multiplier
                retries -= 1
            if session_retries >= 0:
                self._verbose_print(
                    "Too many retries; trying with a new http session.")
                self._http = requests.Session()
            session_retries -= 1
        self._verbose_print("Retries exhausted")
        return response  # Out of tries; return whatever we've got.

    def _handle_any_error(self, response, success_codes={200}):
        # If we are in verbose mode, log any partial requests.
        if self._verbose and len(response.history) > 0:
            for prior_response in response.history:
                try:
                    self._handle_any_error(prior_response)
                except RuntimeError:
                    pass
        if response.status_code not in success_codes:
            print("Failed to download file. "
                  f"Status code: {response.status_code}")
            print("The following information should be included if you open"
                  " an issue for this failure:")
            print(yaml.dump({
                "request": {
                    "method": response.request.method,
                    "url": response.request.url,
                    "headers": dict(response.request.headers)},
                "response": {
                    "status": response.status_code,
                    "reason": response.reason,
                    "history": response.history,
                    "headers": dict(response.headers),
                    "text": response.text[:2000]}}))
            raise RuntimeError(
                f"Failed to {response.request.method} file: "
                f"{response.status_code} ({response.reason})")

    def _object_path(self, hash):
        hash_path = ("" if hash.get_algo() == "sha512"
                     else f"{hash.get_algo()}/")
        return f"{self._path_prefix}{hash_path}/{hash.get_value()}"

    def check_file(self, hash, _project_relpath):
        path = self._object_path(hash)
        response = self._send_request('HEAD', path)
        self._handle_any_error(response,
                               success_codes={200, 400, 403, 404})
        return response.status_code == 200

    def download_file(self, hash, project_relpath, output_file):
        if not self.check_file(hash, project_relpath):
            raise util.DownloadError(
                f"File not available '{project_relpath}"
                f" (hash: {hash.get_value()})")
        path = self._object_path(hash)
        response = self._send_request('GET', path)
        self._handle_any_error(response)
        with open(output_file, 'wb') as file:
            file.write(response.content)
            self._verbose_print("File downloaded successfully!")

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
            self._handle_any_error(response, success_codes={200, 201})
            print("File uploaded successfully!")
