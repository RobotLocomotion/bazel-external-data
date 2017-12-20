"""
@file
Allows uploading data file to a remote.
"""

import os
import sys
import yaml

from bazel_external_data import core, util


def add_arguments(parser):
    parser.add_argument('input_files', type=str, nargs='+')


def run(args, project):
    good = True
    for input_file in args.input_files:
        def action():
            do_check(args, project, input_file)
        if args.keep_going:
            try:
                action()
            except RuntimeError as e:
                good = False
                util.eprint(e)
                util.eprint("Continuing (--keep_going).")
        else:
            action()
    return good


def do_check(args, project, filepath_in):
    filepath = os.path.abspath(filepath_in)
    info = project.get_file_info(filepath)
    remote = info.remote
    project_relpath = info.project_relpath
    hash = info.hash

    def dump_remote_config():
        yaml.dump(info.debug_config(), sys.stdout, default_flow_style=False)

    if args.verbose:
        dump_remote_config()

    if not remote.check_file(hash, project_relpath):
        if not args.verbose:
            dump_remote_config()
        raise RuntimeError(
            "Remote '{}' does not have '{}' ({})".format(
                remote.name, project_relpath, hash))
