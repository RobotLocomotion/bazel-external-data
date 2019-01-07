from __future__ import print_function

import os
import subprocess
import sys
import tarfile


def is_child_path(child_path, parent_path, require_abs=True):
    """Determines if a path is a descendent of a parent path. """
    if require_abs:
        assert os.path.isabs(child_path) and os.path.isabs(parent_path)
    if not parent_path.endswith(os.path.sep):
        parent_path += os.path.sep
    return child_path.startswith(parent_path)


def in_bazel_runfiles(cur_dir=None, project=None):
    """Returns whether a directory was possibly created as part of
    `bazel build` or `bazel run`. """
    # Typically, Bazel runfiles is structured something like
    #   ${bazel_cache}/
    # This should catch if the user has called `bazel run ...`, but not if this
    # command is invoked by `bazel build ...` (or rather, that is called as a
    # tool from a Bazel `genrule`).
    if cur_dir is None:
        cur_dir = os.getcwd()
    pieces = cur_dir.split(os.path.sep)
    if len(pieces) > 1:
        if pieces[-2].endswith('.runfiles'):
            # TODO: This may be overly constrained? This can produce false
            # positives if a user decides to name something this.
            if project is not None:
                return pieces[-1] == project
            else:
                return True
    return False


class DownloadError(RuntimeError):
    """Provides specific error when a file cannot be downloaded. """
    pass


def get_chain(value, key_chain, default=None):
    """Gets a value in a chain of nested dictionaries, with a default if any
    point in the chain does not exist. """
    for key in key_chain:
        if value is None:
            return default
        value = value.get(key)
    return value


def set_chain(base, key_chain, value):
    """Sets a value in a chain of nested dictionaries. """
    if base is None:
        base = {}
    cur = base
    n = len(key_chain)
    for i, key in enumerate(key_chain):
        if i + 1 < n:
            if key not in cur:
                cur[key] = {}
                cur = cur[key]
        else:
            cur[key] = value
    return base


def find_file_sentinel(start_dir, sentinel_file,
                       sentinel_check=os.path.exists, max_depth=100):
    """Finds a sentinel given a check. """
    cur_dir = start_dir
    assert len(cur_dir) > 0
    for _ in range(max_depth):
        assert os.path.isdir(cur_dir)
        test_path = os.path.join(cur_dir, sentinel_file)
        if sentinel_check(test_path):
            return test_path
        cur_dir = os.path.dirname(cur_dir)
        if len(cur_dir) == 0:
            break
    return None


def subshell(cmd, strip=True):
    """Executes subprocess similar to a bash subshell, $(command ...). """
    output = subprocess.check_output(cmd, shell=isinstance(cmd, str))
    if strip:
        return output.strip()
    else:
        return output


def eprint(*args):
    """Prints to stderr. """
    print(*args, file=sys.stderr)


def is_archive(filepath):
    """Determines if a filepath indicates that it's an archive."""
    exts = [
        ".tar.bz2",
        ".tar.gz",
    ]
    for ext in exts:
        if filepath.endswith(ext):
            return True
    return False


def get_bazel_manifest_filename(archive):
    return archive + ".manifest.bzl"


def generate_bazel_manifest(archive):
    manifest = get_bazel_manifest_filename(archive)
    with tarfile.open(archive) as tar, open(manifest, 'w') as f:
        # Get all files.
        members = []
        for member in tar.getmembers():
            if member.isfile() or member.issym():
                members.append(member)
            elif member.isdir():
                # Ignore directories.
                pass
            else:
                # Puke.
                raise RuntimeError(
                    "Bad tarfile file type: {} - {}".format(
                        member.name, member.type))
        # Generate text.
        f.write("# Auto-generated manifest for consumption in both Bazel")
        f.write(" and Python.\n")
        f.write("manifest = dict(\n")
        f.write("    files = [\n")
        names = [member.name for member in members]
        for name in sorted(names):
            f.write("        \"{}\",\n".format(name))
        f.write("    ],\n")
        f.write(")\n")
