"""
@file
Uploads a file or set of files for this project.
"""

import os
import sys

from bazel_external_data.util import eprint


def add_arguments(parser):
    parser.add_argument('filepaths', type=str, nargs='+')
    parser.add_argument(
        '--local_only', action='store_true',
        help="Only update local file information (e.g. hash file), but do not" +
             "upload the file.")


def run(args, project):
    good = True
    for filepath in args.filepaths:
        def action():
            do_upload(args, project, filepath)
        if args.keep_going:
            try:
                action()
            except RuntimeError as e:
                good = False
                eprint(e)
                eprint("Continuing (--keep_going).")
        else:
            action()
    return good


def do_upload(args, project, filepath):
    info = project.get_file_info(os.path.abspath(filepath), needs_hash=False)
    remote = info.remote
    hash = info.hash
    project_relpath = info.project_relpath
    orig_filepath = info.orig_filepath

    if args.verbose:
        yaml.dump(info.debug_config(), sys.stdout, default_flow_style=False)

    if not args.local_only:
        hash = remote.upload_file(
            hash.hash_type, project_relpath, orig_filepath)
    else:
        hash = hash.compute(orig_filepath)
    project.update_file_info(info, hash)
