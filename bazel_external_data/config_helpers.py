"""
@file
Helpers for configuration finding, specific to (a) general
`bazel_external_data` configuration and (b) Bazel sandbox path reversal
within `bazel_external_data`.
"""

import os
import yaml
import copy

from bazel_external_data import util


def _resolve_dir(filepath):
    # Returns the directory of a file, or the directory if passed directly.
    if os.path.isdir(filepath):
        return filepath
    else:
        return os.path.dirname(filepath)


def find_project_root(guess_filepath, sentinel, project_name):
    """Finds the project root, accounting for oddities when in Bazel
    execroot-land. This will attempt to find the file sentinel.
    """

    def sentinel_check(filepath):
        if os.path.exists(filepath):
            if project_name is None:
                return True
            else:
                # Open and read the file to see if we have the desired name.
                with open(filepath) as f:
                    config = yaml.safe_load(f)
                return config['project'] == project_name
        else:
            return False

    start_dir = _resolve_dir(guess_filepath)
    root_file = util.find_file_sentinel(start_dir, sentinel, sentinel_check)
    if root_file is None:
        hint = ""
        if project_name:
            hint = " (with project = '{}')".format(project_name)
        raise RuntimeError(
            "Could not find sentinel: {}{}".format(sentinel, hint))
    # If our root_file is a symlink, then this should be due to a Bazel
    # execroot. Record the original directory as a possible alternative.
    root_alternatives = []
    if os.path.islink(root_file):
        # Assume that the root file is symlink'd because Bazel has linked it in.
        # Read this to get the original path.
        alt_root_file = os.readlink(root_file)
        assert os.path.isabs(alt_root_file)
        if os.path.islink(alt_root_file):
            raise RuntimeError(
                "Sentinel '{}' should only have one level of an absolute-path" +
                "symlink.".format(sentinel))
        (alt_root_file, root_file) = (root_file, alt_root_file)
        root_alternatives.append(os.path.dirname(alt_root_file))
    root = os.path.dirname(root_file)
    return (root, root_alternatives)


def parse_config_file(config_file, add_filepath=True):
    """ Parse a configuration file.
    @param add_filepath
        Adds `config_file` to the root level for debugging purposes. """
    with open(config_file) as f:
        config = yaml.safe_load(f)
    if config is None:
        config = {}
    if add_filepath:
        config['config_file'] = config_file
    return config


def merge_config(base_config, new_config, in_place=False):
    """Recursively merges configurations. """
    if base_config is None:
        return new_config
    if not in_place:
        base_config = copy.deepcopy(base_config)
    if new_config is None:
        return base_config
    # Merge a configuration file.
    for key, new_value in new_config.items():
        base_value = base_config.get(key)
        if isinstance(base_value, dict):
            assert isinstance(new_value, dict), \
                   "New value must be dict: {} - {}".format(key, new_value)
            # Recurse.
            value = merge_config(base_value, new_value, in_place=True)
        else:
            # Overwrite.
            value = new_value
        base_config[key] = value
    return base_config
