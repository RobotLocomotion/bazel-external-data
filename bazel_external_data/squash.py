#!/usr/bin/env python3

"""
Squash a set of new files from a `head` remote to get the minimal set of new of
files for `base`. These files are staged into `merge`.
"""

# TODO(eric.cousineau): Upstream this into `bazel_external_data` if it can ever
# be generalized to be Girder-agnostic.

import os
import sys
from tempfile import mkdtemp
import yaml

from bazel_external_data.core import load_project
from bazel_external_data.util import eprint


def add_arguments(parser):
    parser.add_argument(
        "base", type=str, help="Base remote (e.g. `master`)")
    parser.add_argument(
        "head", type=str, help="Head remote (e.g. `devel`)")
    parser.add_argument(
        "merge", type=str,
        help="Merge remote (e.g. `merge`) to contain the files from `head` " +
             "which are new to `base`")
    parser.add_argument(
        "--files", type=str, nargs='*', default=None,
        help="Files to check. By default, checks all files in the project.")


def run(args, project):
    # Ensure that all remotes are disjoint.
    assert args.base != args.head and args.head != args.merge, (
        "Must supply unique remotes")

    if args.verbose:
        print("base: {}".format(args.base))
        print("head: {}".format(args.head))
        print("merge: {}".format(args.merge))

    # Remotes.
    base = project.get_remote(args.base)
    head = project.get_remote(args.head)
    merge = project.get_remote(args.merge)

    stage_dir = mkdtemp(prefix="bazel_external_data-merge-")

    if args.verbose:
        print("stage_dir: {}".format(stage_dir))

    # List files.
    if args.files is None:
        files = project.get_registered_files()
    else:
        files = [os.path.abspath(file) for file in args.files]

    def do_squash(info):
        if args.verbose:
            yaml.dump(
                info.debug_config(), sys.stdout, default_flow_style=False)
        # If the file already exists in `base`, no need to do anything.
        if base.check_file(info.hash, info.project_relpath):
            print("- Skip: {}".format(info.project_relpath))
            return
        # File not already uploaded: download from `head` to `stage_dir`, then
        # upload to `merge`.
        file_stage_abspath = os.path.join(stage_dir, info.project_relpath)
        file_stage_dir = os.path.dirname(file_stage_abspath)
        os.makedirs(file_stage_dir, exist_ok=True)
        head.download_file(
            info.hash, info.project_relpath, file_stage_abspath, symlink=True)
        # Upload file to `merge`.
        hash_merge = merge.upload_file(
            info.hash.hash_type, info.project_relpath, file_stage_abspath)
        assert info.hash == hash_merge  # Sanity check
        print("Uploaded: {}".format(info.project_relpath))

    good = True
    for file_abspath in files:
        info = project.get_file_info(file_abspath, needs_hash=True)
        def action():
            do_squash(info)
        if args.keep_going:
            try:
                action()
            except RuntimeError as e:
                good = False
                eprint(e)
                eprint("Continuing (--keep_going)")
        else:
            action()
    return good
