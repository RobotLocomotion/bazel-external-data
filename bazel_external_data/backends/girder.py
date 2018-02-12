from datetime import datetime
import json
import os
import requests
import yaml

from bazel_external_data import util
from bazel_external_data.core import Backend


class GirderHashsumBackend(Backend):
    """ Supports Girder servers where authentication may be needed (e.g. for uploading, possibly downloading). """
    def __init__(self, config, project_root, user):
        # Until there is a Girder plugin that can discriminate based on folder_id,
        # have configuration disable uploading on "master".
        # @ref https://github.com/girder/girder/issues/2446
        Backend.__init__(self, config, project_root, user)
        self._disable_upload = config.get('disable_upload', False)
        self._url = config['url']
        self._api_url = "{}/api/v1".format(self._url)
        self._folder_path = config['folder_path']
        # Get (optional) authentication information.
        url_config_node = util.get_chain(user.config, ['girder', 'url', self._url])
        self._api_key = util.get_chain(url_config_node, ['api_key'])
        self._token = None
        self._girder_client = None

    def _request(self, endpoint, params={}, method="get", stream=False):
        def json_value(value):
            if isinstance(value, str):
                return value
            else:
                return json.dumps(value)
        headers = {}
        if self._token:
            headers = {"Girder-Token": self._token}
        params = {key: json_value(value) for key, value in params.iteritems()}
        func = getattr(requests, method)
        r = func(self._api_url + endpoint, params=params, headers=headers, stream=stream)
        r.raise_for_status()
        return r

    def _get_folder_id(self):
        key_chain = ['url', self._url, 'folder_ids', self._folder_path]
        response = self._request('/resource/lookup', params={"path": self._folder_path}).json()
        assert response["_modelType"] == "folder"
        return str(response["_id"])

    def _authenticate_if_needed(self):
        if self._api_key is not None and self._token is None:
            response = self._request("/api_key/token", method="post", params={"key": self._api_key}).json()
            self._token = response["authToken"]["token"]

    def _is_part_of_folder(self, hash):
        # Get files for the given hashsum.
        files = self._request("/file/hashsum/{algo}/{hash}".format(algo=hash.get_algo(), hash=hash.get_value())).json()
        for file in files:
            id = file["_id"]
            # Get path.
            path = self._request("/resource/{id}/path".format(id=id), params={"type": "file"}).json()
            if path.startswith(self._folder_path + "/"):
                return True
        return False

    def check_file(self, hash, project_relpath):
        # Ensure the file exists in the folder.
        self._authenticate_if_needed()
        return self._is_part_of_folder(hash)

    def download_file(self, hash, project_relpath, output_file):
        self._authenticate_if_needed()
        if not self.check_file(hash, project_relpath):
            raise util.DownloadError("File not available in Girder folder '{}': {} (hash: {})".format(self._folder_path, project_relpath, hash))
        r = self._request("/file/hashsum/{algo}/{hash}/download"
                          .format(algo=hash.get_algo(), hash=hash.get_value()))
        with open(output_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)

    def _get_girder_client(self):
        # @note We import girder_client here, as only uploading requires it at present.
        # If `girder_client` can be imported via Bazel with minimal pain, then we can bubble
        # this up to the top-level.
        import girder_client
        if self._girder_client is None:
            self._girder_client = girder_client.GirderClient(apiUrl=self._api_url)
            self._girder_client.authenticate(apiKey=self._api_key)
        return self._girder_client

    def upload_file(self, hash, project_relpath, filepath):
        if self._disable_upload:
            raise RuntimeError("Upload disabled")
        item_name = "%s %s" % (os.path.basename(filepath), datetime.utcnow().isoformat())
        folder_id = self._get_folder_id()

        print("api_url ............: %s" % self._api_url)
        print("folder_path ..........: %s" % self._folder_path)
        print("folder_id ..........: %s" % folder_id)
        print("filepath ...........: %s" % filepath)
        print("hash ...............: %s" % hash)
        print("item_name ..........: %s" % item_name)
        print("project_relpath .: %s" % project_relpath)
        # TODO(eric.cousineau): Include `project.name` in the versioning!
        # TODO(eric.cousineau): Add the visualization key for the Girder `vtk.js` stuff.
        ref = json.dumps({'versionedFilePath': project_relpath})
        gc = self._get_girder_client()
        size = os.stat(filepath).st_size
        with open(filepath, 'rb') as fd:
            print("Uploading: {}".format(filepath))
            gc.uploadFile(folder_id, fd, name=item_name, size=size, parentType='folder', reference=ref)


def get_backends():
    return {
        "girder_hashsum": GirderHashsumBackend,
    }
