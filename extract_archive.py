"""Extracts an archive, ensuring that it matches a given `*.bzl` manifest.

This manifest should have been generated via `generate_bazel_manifest` in
`bazel_external_data.util`. The manifest can be generated using:

    <cli> upload --local_only --manifest_generation=force <archive>
"""

import argparse
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument("archive", type=str)
parser.add_argument("--manifest", type=str)
parser.add_argument("--output_dir", type=str)
parser.add_argument("--strip_prefix", type=str)

args = parser.parse_args()

with open(args.manifest) as f:
    manifest_text = f.read()
manifest_locals = {}
# Parse manifest, assuming it's Python-friendly.
exec(manifest_text, globals(), manifest_locals)
manifest = manifest_locals["manifest"]

# First require the manifest exactly match the files present in the archive.
tar = tarfile.open(args.archive, 'r')
# - We only allow regular files; not going to deal with symlinks or devices for
# now.
members = [member for member in tar.getmembers()
           if member.isfile() or member.issym()]
tar_files = sorted((member.name for member in members))
manifest_files = sorted(manifest["files"])
# Demand exact matching.
if tar_files != manifest_files:
    tar_not_manifest = set(tar_files) - set(manifest_files)
    manifest_not_tar = set(manifest_files) - set(tar_files)
    msg = "  Files in tar, not manifest:\n"
    msg += "    " + "\n    ".join(tar_not_manifest) + "\n\n"
    msg += "  Files in manifest, not tar:\n"
    msg += "    " + "\n    ".join(manifest_not_tar) + "\n"
    raise RuntimeError(
        "Mismatch in manifest and archive; please regenerate archive "
        "manifest.\n\n"
        "  To fix: <cli> upload --local_only --manifest_generation=force " +
        "<archive>\n\n" +
        msg)

# Apply path transformations.
# According to https://stackoverflow.com/a/8261083/7829525, we can magically
# alter the `.name` field of a member to change where it gets extracted to.
def filter_members(members):
    for member in members:
        if member.name.startswith(args.strip_prefix):
            old = member.name
            member.name = member.name[len(args.strip_prefix):]
            yield member

# Extract all files.
tar.extractall(path=args.output_dir, members=filter_members(members))
