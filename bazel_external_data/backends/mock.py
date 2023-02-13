import shutil
import os

from bazel_external_data import util, hashes
from bazel_external_data.core import Backend


class MockBackend(Backend):
    """ A mock backend for testing. """
    def __init__(self, config, project_root, user):
        Backend.__init__(self, config, project_root, user)
        self._dir = os.path.join(project_root, config['dir'])
        self._upload_dir = os.path.join(project_root, config['upload_dir'])
        self._hash_type = hashes.sha512

        # Crawl through files and compute hashes.
        self._map = {}
        def crawl(cur_dir):
            for file in os.listdir(cur_dir):
                filepath = os.path.join(cur_dir, file)
                if os.path.isfile(filepath):
                    hash = self._hash_type.compute(filepath)
                    self._map[hash] = filepath
        crawl(self._dir)
        if os.path.exists(self._upload_dir):
            crawl(self._upload_dir)

    def _check_hash_type(self, hash):
        if hash.hash_type != self._hash_type:
            raise RuntimeError("Mock backend only supports {}, not {}".format(self._hash_type, hash.hash_type))

    def check_file(self, hash, project_relpath):
        self._check_hash_type(hash)
        return hash in self._map

    def download_file(self, hash, project_relpath, output_file):
        self._check_hash_type(hash)
        filepath = self._map.get(hash)
        if filepath is None:
            raise util.DownloadError("Unknown hash: {}".format(hash))
        shutil.copy(filepath, output_file)

    def upload_file(self, hash, project_relpath, filepath):
        self._check_hash_type(hash)
        assert hash not in self._map
        dest = os.path.join(self._upload_dir, hash.get_value())
        assert not os.path.exists(dest)
        dest_dir = os.path.dirname(dest)
        os.makedirs(dest_dir, exist_ok=True)
        # Copy the file.
        shutil.copy(filepath, dest)
        # Store the SHA.
        self._map[hash] = dest
