#!/usr/bin/env python3

# Provides a mechanism to provide a subset of `//:cli` functionality to
# leverage external data in repository rules.
import os
import sys

src_dir = os.path.dirname(os.readlink(os.path.abspath(__file__)))
# Trace back to source workspace so we can use existing source.
env = dict(os.environ)
env["PYTHONPATH"] = src_dir + ":" + env.get("PYTHONPATH", "")
args = [sys.executable, "-m", "bazel_external_data.cli"] + sys.argv[1:]
os.execve(args[0], args, env)
