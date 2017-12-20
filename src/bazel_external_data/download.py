from __future__ import absolute_import, print_function
import argparse
import os
import sys
import yaml

from bazel_external_data import core, util, config_helpers


def add_arguments(parser):
    # TODO(eric.cousineau): Consider making this interpret inputs/outputs as
    # pairs.
    # TODO(eric.cousineau): Make a `--quick` option to ignore checking SHAs, if
    # performance is impacted.
    parser.add_argument(
        '-o', '--output', dest='output_file', type=str,
        help='Output destination. If specified, only one input file may ' +
             'be provided.')
    parser.add_argument(
        'input_files', type=str, nargs='+',
        help='Files to be downloaded. If --output is not provided, the ' +
             'output destination is inferred from the input path.')
    parser.add_argument(
        '-f', '--force', action='store_true',
        help='Overwrite existing output file.')
    parser.add_argument(
        '--no_cache', action='store_true',
        help='Always download, and do not cache the result.')
    parser.add_argument(
        '--symlink', action='store_true',
        help='Use a symlink from the cache rather than copying the file.')


def run(args, project):
    good = True
    if args.output_file:
        if len(args.input_files) != 1:
            raise RuntimeError("Can only specify one input file with --output")
        input_file = os.path.abspath(args.input_files[0])
        info = project.get_file_info(input_file)
        output_file = os.path.abspath(args.output_file)
        do_download(args, project, info, output_file)
    else:
        for input_file in args.input_files:
            input_file = os.path.abspath(input_file)
            info = project.get_file_info(input_file)
            output_file = info.orig_filepath
            def action():
                do_download(args, project, info, output_file)
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


def do_download(args, project, info, output_file):
    project_relpath = info.project_relpath
    remote = info.remote
    hash = info.hash

    if args.verbose:
        yaml.dump(info.debug_config(), sys.stdout, default_flow_style=False)
    # Ensure that we do not overwrite existing files.
    if os.path.isfile(output_file):
        if args.force:
            os.remove(output_file)
        else:
            raise RuntimeError(
                "Output file already exists: {}".format(output_file) +
                "\n  (Use `--keep_going` to ignore or `--force` to " +
                "overwrite.)")
    download_type = remote.download_file(
        hash, project_relpath, output_file,
        use_cache=not args.no_cache,
        symlink=args.symlink)
