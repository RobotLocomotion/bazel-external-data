#!/usr/bin/env python

import argparse
import os
import sys
import traceback
import yaml

from bazel_external_data import config_helpers, download, upload, check
from bazel_external_data.core import load_project
from bazel_external_data.util import eprint, in_bazel_runfiles

assert __name__ == '__main__'

parser = argparse.ArgumentParser()
parser.add_argument('--project_root_guess', type=str, default='.',
                    help='File path to guess the project root.')
parser.add_argument('--project_name', type=str, default=None,
                    help='Constrain finding a project root to the given name.')
parser.add_argument('--user_config', type=str, default=None,
                    help='Override user configuration.')
parser.add_argument('-k', '--keep_going', action='store_true',
                    help='Attempt to keep going.')
parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='Dump configuration and show command-line arguments. '
         'WARNING: Will print out information in user configuration ' +
         '(e.g. keys) as well!')

subparsers = parser.add_subparsers(dest="command")

download.add_arguments(subparsers.add_parser("download"))
upload.add_arguments(subparsers.add_parser("upload"))
check.add_arguments(subparsers.add_parser("check"))

args = parser.parse_args()

# Do not allow running under Bazel unless we have a guess for the project root
# from an input file.
if in_bazel_runfiles() and not args.project_root_guess:
    eprint("ERROR: Do not run this command via `bazel run`. " +
           "Use a wrapper to call the binary.")
    eprint("  (If you are writing a test in Bazel, ensure that " +
           "you pass `--project_root_guess=$(location <target>)`.)")
    exit(1)

if args.verbose:
    eprint("cmdline:")
    eprint("  pwd: {}".format(os.getcwd()))
    eprint("  argv[0]: {}".format(sys.argv[0]))
    eprint("  argv[1:]: {}".format(sys.argv[1:]))

project = load_project(
    os.path.abspath(args.project_root_guess),
    user_config_file=args.user_config,
    project_name=args.project_name)

if args.verbose:
    yaml.dump({"user_config": project.user.config}, sys.stdout,
              default_flow_style=False)
    yaml.dump({"project_config": project.config}, sys.stdout,
              default_flow_style=False)

# Execute command.
status = False
try:
    if args.command == 'download':
        status = download.run(args, project)
    elif args.command == 'upload':
        status = upload.run(args, project)
    elif args.command == "check":
        status = check.run(args, project)
except Exception as e:
    if args.verbose:
        # Full stack trace.
        traceback.print_exc(file=sys.stderr)
    else:
        # Just the error.
        eprint(e)

if status is not None and status is not True:
    eprint("Encountered error")
    exit(1)
