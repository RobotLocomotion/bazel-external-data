import os
import shutil
import stat
import subprocess
import uuid

from bazel_external_data import util, config_helpers, hashes

PROJECT_CONFIG_FILE = ".external_data.yml"
USER_CONFIG_FILE_DEFAULT = os.path.expanduser(
    "~/.config/bazel_external_data/config.yml")
USER_CONFIG_DEFAULT = {
    "core": {
        "cache_dir": os.path.expanduser("~/.cache/bazel_external_data"),
    },
}


def load_project(guess_filepath, project_name=None, user_config_file=None):
    """Loads a project.
    @param guess_filepath
        Filepath where to start guessing where the project root is.
    @param user_config_file
        Overload for user configuration.
    @param project_name
        Constrain finding the project root to project files with the provided
        project name (for working with nested projects).
    @return A `Project` instance.
    @see test/bazel_external_data_config
    """
    if user_config_file is None:
        user_config_file = USER_CONFIG_FILE_DEFAULT
    if os.path.exists(user_config_file):
        user_config = config_helpers.parse_config_file(user_config_file)
    else:
        user_config = {}
    user_config = config_helpers.merge_config(USER_CONFIG_DEFAULT, user_config)
    user = User(user_config)
    # Start guessing where the project lives.
    project_root, root_alternatives = config_helpers.find_project_root(
        guess_filepath, PROJECT_CONFIG_FILE, project_name)
    # Load configuration.
    project_config_file = os.path.join(
        project_root, os.path.join(project_root, PROJECT_CONFIG_FILE))
    project_config = config_helpers.parse_config_file(project_config_file)
    # Inject project information.
    project_config['root'] = project_root
    # Cache symlink root, and use this to get relative workspace path if the
    # file is specified in the symlink'd directory (e.g. Bazel runfiles).
    project_config['root_alternatives'] = root_alternatives
    # We must place this import here given that `Backend` is defined in this
    # module.
    from bazel_external_data import backends
    project = Project(project_config, user, backends.get_default_backends())
    return project


class Project(object):
    """Specifies a project's structure, remotes, and determines the mapping
    between files and their remotes (for download / uploading). """
    def __init__(self, config, user, backends):
        self.config = config
        self.user = user
        self._backends = backends
        # Load project-specific settings.
        self.name = self.config['project']
        self.root_path = self.config['root']
        self._root_path_alternatives = self.config.get('root_alternatives', [])
        # Load frontend.
        self._frontend = HashFileFrontend()
        # Remotes.
        self._remote_selected = self.config['remote']
        self._remotes = {}
        self._remote_is_loading = []

    def _load_backend(self, backend_type, config):
        """Loads a backend given the type and its configuration. """
        backend_cls = self._backends[backend_type]
        return backend_cls(config, self.root_path, self.user)

    def get_remote(self, name):
        """Gets a remote by name, loading on demand. """
        remote = self._remotes.get(name)
        if remote:
            return remote
        # Check against dependency cycles.
        if name in self._remote_is_loading:
            raise RuntimeError(
                "Cycle detected for 'remote': {}".format(
                    self._remote_is_loading))
        self._remote_is_loading.append(name)
        # Load remote.
        remote_config = self.config['remotes'][name]
        remote = Remote(remote_config, name, self.user.cache_dir,
                        self._load_backend, self.get_remote)
        # Update.
        self._remote_is_loading.remove(name)
        self._remotes[name] = remote
        return remote

    def _get_relpath(self, filepath):
        """Gets filepah relative to project root, using alternative roots if
        viable. """
        assert os.path.isabs(filepath)
        root_paths = [self.root_path] + self._root_path_alternatives
        # @note This will not handle a nested root.
        # (e.g. if an alternative is a child or parent of another path)
        for root_path in root_paths:
            if util.is_child_path(filepath, root_path):
                return os.path.relpath(filepath, root_path)
        raise RuntimeError("Path is not a child of given project")

    def get_file_info(self, input_file, needs_hash=True):
        """Gets file information from a given filepath.

        @returns `FileInfo` object, `info`.
            Remote operations (uploading, download, etc.) should accessed
            through `info.remote`."""
        hash, orig_filepath = (
            self._frontend.get_hash_file_info(input_file, needs_hash))
        project_relpath = self._get_relpath(orig_filepath)
        remote = self.get_remote(self._remote_selected)
        return FileInfo(hash, remote, project_relpath, orig_filepath)

    def update_file_info(self, info, hash):
        """Writes hashsum for a given set of file information. """
        self._frontend.update_hash_file_info(info.orig_filepath, hash)

    def get_registered_files(self, use_relpath=False):
        """Returns a list of relpaths of files contained within the project."""
        output = subprocess.check_output(
            "find '{root}' -name '*.sha512'".format(root=self.root_path),
            shell=True).decode("utf8")
        files = self._frontend.find_registered_file_abspaths(self.root_path)
        if use_relpath:
            return [self._get_relpath(file) for file in files]
        else:
            return files


class User(object):
    """Stores user-level configuration. """
    def __init__(self, config):
        self.config = config
        self.cache_dir = os.path.expanduser(config['core']['cache_dir'])


class HashFileFrontend(object):
    """Determines file information based on neighboring hash file. """
    def __init__(self):
        self._hash_type = hashes.sha512
        self._suffix = ".sha512"

    def _get_orig_file(self, hash_file):
        # Return original file if its a hash file, or return None if not a hash
        # file.
        assert os.path.isabs(hash_file)
        if not hash_file.endswith(self._suffix):
            return None
        else:
            return hash_file[:-len(self._suffix)]

    def _is_hash_file(self, input_file):
        return self._get_orig_file(input_file) is not None

    def _get_hash_file(self, input_file):
        assert not self._is_hash_file(input_file)
        return input_file + self._suffix

    def find_registered_file_abspaths(self, start_dir):
        """Gets all registered file abspaths."""
        output = subprocess.check_output(
            "find '{root}' -name '*{suffix}'".format(
                root=start_dir, suffix=self._suffix),
            shell=True).decode("utf8")
        return output.strip().split("\n")

    def get_hash_file_info(self, input_file, needs_hash):
        """Gets hash file information. """
        assert os.path.isabs(input_file)
        orig_filepath = self._get_orig_file(input_file) or input_file
        hash_file = self._get_hash_file(orig_filepath)
        if not os.path.isfile(hash_file):
            if needs_hash:
                raise RuntimeError(
                    "ERROR: Hash file not found: {}".format(hash_file))
            else:
                hash = self._hash_type.create_empty()
                hash.filepath = orig_filepath
        else:
            # Load the hash.
            with open(hash_file, 'r') as f:
                hash = self._hash_type.create(
                    f.read().strip(), filepath=orig_filepath)
        return (hash, orig_filepath)

    def update_hash_file_info(self, orig_filepath, hash):
        """Writes hashsum for a given file. """
        assert not hash.is_empty()
        assert hash.hash_type == self._hash_type
        hash_file = self._get_hash_file(orig_filepath)
        assert hash.filepath == orig_filepath
        with open(hash_file, 'w') as f:
            f.write(hash.get_value())


class FileInfo(object):
    """Specifies general information for a given file. """
    def __init__(self, hash, remote, project_relpath, orig_filepath):
        # This is the *project* hash, NOT the has of the present file.
        # If None, then that means the file is not yet part of the project.
        self.hash = hash
        # Remote for the given file.
        self.remote = remote
        # Path of the file (not the hash file) relative to the project root.
        self.project_relpath = project_relpath
        # Actual file.
        self.orig_filepath = orig_filepath

    def debug_config(self):
        return [{
            "hash": str(self.hash),
            "remote": {self.remote.name: self.remote.config},
            "project_relpath": self.project_relpath,
            "orig_filepath": self.orig_filepath,
        }]


class Remote(object):
    """Provides cache- and hierarchy-friendly access to a backend. """
    def __init__(self, config, name,
                 cache_dir, load_backend, get_remote):
        self.config = config
        self.name = name
        self._cache_dir = cache_dir
        self._backend = load_backend(self.config['backend'], config)
        self.overlay = None
        overlay_name = self.config.get('overlay')
        if overlay_name is not None:
            self.overlay = get_remote(overlay_name)

    def check_file(self, hash, project_relpath, check_overlay=True):
        """ Returns whether this remote (or its overlay) has a given SHA. """
        if self._backend.check_file(hash, project_relpath):
            return True
        elif check_overlay and self.overlay:
            return self.overlay.check_file(hash, project_relpath)

    def _download_file_direct(self, hash, project_relpath, output_file):
        # Downloads a file directly and checks the SHA.
        # @pre `output_file` should not exist.
        assert not os.path.exists(output_file)
        try:
            self._backend.download_file(hash, project_relpath, output_file)
            hash.compare_file(output_file)
        except util.DownloadError as e:
            if self.overlay:
                self.overlay._download_file_direct(
                    hash, project_relpath, output_file)
            else:
                raise e

    def download_file(self, hash, project_relpath, output_file,
                      use_cache=True, symlink=True):
        """Downloads a file.
        @param hash
            Comptued hashsum for the file.
        @param project_relpath
            @see Backend.download_file
        @param use_cache
            Uses cache file in the specified cache directory.
        @param symlink
            If `use_cache` is true, this will place a symlink to the read-only
            cache file at `output_file`.
        @returns 'cache' if there was a cachce hit, 'download' otherwise.
        """
        assert os.path.isabs(output_file)
        assert not os.path.exists(output_file)

        # Helper functions.

        def download_file_direct(output_file):
            # Assuming we're on Unix (where `os.rename` is atomic), use a
            # tempfile to avoid race conditions.
            tmp_file = os.path.join(
                os.path.dirname(output_file), str(uuid.uuid4()))
            try:
                self._download_file_direct(hash, project_relpath, tmp_file)
            except util.DownloadError as e:
                util.eprint("ERROR: For remote '{}'".format(self.name))
                raise e
            os.rename(tmp_file, output_file)

        def get_cached(check_sha):
            # Can use cache. Copy to output path.
            if symlink:
                os.symlink(cache_path, output_file)
            else:
                shutil.copy(cache_path, output_file)
                # Ensure file is writeable.
                mode_original = os.stat(output_file)[stat.ST_MODE]
                os.chmod(output_file, mode_original | stat.S_IWUSR)
            # On error, remove cached file, and re-download.
            if check_sha:
                if not hash.compare_file(output_file, do_throw=False):
                    util.eprint("Hashsum mismatch. " +
                                "Removing old cached file, re-downloading.")
                    os.remove(cache_path)
                    if os.path.islink(output_file):
                        # In this situation, the cache was corrupted, and
                        # Bazel recompilation, but the symlink is still in
                        # Bazel-space. Remove the symlink, so that we do not
                        # download into a symlink (which complicates the logic
                        # in `download_and_cache`).
                        os.remove(output_file)
                    download_and_cache()

        def download_and_cache():
            # TODO(eric.cousineau): Consider locking the file.
            download_file_direct(cache_path)
            # Make cache file read-only.
            mode_write_all = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
            mode_original = os.stat(cache_path)[stat.ST_MODE]
            os.chmod(cache_path, mode_original & ~mode_write_all)
            # Use cached file since `get_download()` has already checked the
            # hash.
            get_cached(False)

        # Actions.
        if use_cache:
            cache_path = _get_hash_cache_path(self._cache_dir, hash,
                                              create_dir=True)
            if os.path.isfile(cache_path):
                get_cached(True)
                return 'cache'
            else:
                download_and_cache()
                return 'download'
        else:
            download_file_direct(output_file)
            return 'download'

    def upload_file(self, hash_type, project_relpath, filepath,
                    check_overlay=True):
        """
        Uploads a file.
        If `check_overlay` is True, the file will not be uploaded the this
        remote if the overlay already has it.
        """
        assert os.path.isabs(filepath)
        hash = hash_type.compute(filepath)
        if self.check_file(hash, project_relpath, check_overlay=check_overlay):
            note = (
                check_overlay and "checking overlay" or "ignoring overlay")
            print("File already uploaded ({})".format(note))
        else:
            self._backend.upload_file(hash, project_relpath, filepath)
        return hash


class Backend(object):
    """Checks, downloads, and uploads a file from a storage mechanism. """
    def __init__(self, config, project_root, user):
        pass

    def check_file(self, hash, project_relpath):
        """ Determines if the storage mechanism has a given SHA. """
        raise NotImplemented()

    def download_file(self, hash, project_relpath, output_path):
        """ Downloads a file from a given hash to a given output path.
        @param project_relpath
            File path relative to project.
        """
        raise RuntimeError("Downloading not supported for this backend")

    def upload_file(self, hash, project_relpath, filepath):
        """ Uploads a file from an output path given a SHA.
        @param project_relpath
            Same as for `download_file`, but must not be None.
        @note This hash should be assumed to be valid. """
        raise RuntimeError("Uploading not supported for this backend")


def _get_hash_cache_path(cache_dir, hash, create_dir=True):
    # Gets the cache path for a given hash file.
    hash_algo = hash.get_algo()
    hash_value = hash.get_value()
    out_dir = os.path.join(
        cache_dir, hash_algo, hash_value[0:2], hash_value[2:4])
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, hash_value)
