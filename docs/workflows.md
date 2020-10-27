# Workflows

## Start Drafting a Large File

Say you're in `:/data`, and want to author `dragon.obj` to be used in a Bazel
test.

1. In your package's `BUILD` file, ensure that you have loaded the appropriate macros:

        load("//tools/external_data:external_data.bzl",
            "external_data",
        )

1. Add a Bazel target for this file indicating that it's external data and that you're in the process of developing the file. In `:/data/BUILD`:

        external_data(
            file = "dragon.obj",
            mode = "devel",  # Delete once you've uploaded.
        )

    NOTE: Under the hood, this simply uses `exports_files(...)` in "devel" mode
    to make the file a proper target, using the same name. This is useful for later points in time, when you want to edit a file that has already been versioned.

2. Write a test, e.g. `://test:inspect_dragon`, that consumes this file:

        sh_test(
            name = "inspect_dragon",
            ...,
            args = ["data/dragon.obj"],
            data = ["//data:dragon.obj"],
            tags = ["external_data"],  # Specify so that we can discriminate.
        )

    Run the test to ensure it works as expected.


## Upload the File for Deployment

1. Run the `upload` script given the absolute path of the desired file:

        cd data
        # Edit ./dragon.obj...
        ../tools/external_data/cli upload ./dragon.obj

    If the file does not already exist on the desired server, this will upload the file. This will also update `dragon.obj.sha512` to reflect that the server-side information.

    NOTE: You may upload multiple files via the CLI interface.

2. Update `:/data/BUILD` to indicate that you're now using the uploaded version (this tells Bazel to expect `dragon.obj.sha512`):

        external_data(
            file = "dragon.obj",
        )

3. To test if Bazel can download this file, execute this in `:/data`:

        bazel build :dragon.obj

    This should have downloaded, cached, and exposed this file in Bazel's workspace. Now run `://test:inspect_dragon` (which should use Bazel's cached version) and ensure this works.

    Bazel should have placed its symlink of the file in `bazel-out/local-fastbuild/genfiles/data/basic.bin`. If you want to Edit the file and ensure that Bazel takes these changes, see below.

    If you want to be able to run a test from your workspace, using something like `./bazel-bin/my_package/my_target`, you must download the file (or symlink) in your workspace to ensure it's accessible. See further below for more information about this.

4. Now commit the `*.sha512` file in Git.


## Edit the File Later

Let's say you've removed `dragon.obj` from `:/data`, but a month later you wish to revise it. To update the file:

1. Re-download the object (using `-f | --force` to remove the existing file):

        cd data
        ../tools/external_data/cli download -f ./dragon.obj.sha512

    **NOTE**: You may also run `../tools/external_data/cli download -f ./dragon.obj`. It will recognize the intended object.

2. Change `:/data/BUILD` back to development mode:

        external_data(
            file = "dragon.obj",
            mode = "devel",  # Add this line back in.
        )

3. Make the appropriate changes.

4. Follow the steps in "Upload the File for Deployment".

## Use `*.sha512` groups in `BUILD`

For groups of large data files, you could specify individual Bazel `external_data` targets, or explicitly list the files in  `external_data_group`.

However, if you have a large set of `*.${ext}.sha512` files, it may be easier to use the workspace's directory structure to glob these files. (You cannot reliably use `*.${ext}` without the suffix because these files would not exist normally.)

As an example in `:/data`:

    load("//tools:external_data.bzl",
        "external_data_group",
        "get_original_files",
    )

    external_data_group(
        name = "meshes",
        files = get_original_files(
            glob(['**/*.obj.sha512'])
        ),
    )

You may now use `:meshes` in tests to get all of these files.

If you wish to expose all of these files within the Bazel build sandbox, you may execute:

    bazel build :meshes

NOTE: This interface will cache the files under the cache directory specified in your user configuration, and thus you will not need to re-download these files.


## Edit Files in a `*.sha512` group

You may also use `mode = "devel"` in `external_data_group` if you wish to edit *all* of the files. If you do want this, you *must* have all of the files available in your workspace. (See "Download a Set of Files".)

If you want to edit a certain file in a group, you may use
`external_data_group(..., files_devel = ...)`. As an example:

    external_data_group(
        name = "meshes_nondevel",
        files = get_original_files(
            glob(['**/*.obj.sha512'])
        ),
        files_devel = ['robot/to_edit.obj'],
    )

**NOTE**: You can extend this to use an `*.obj` files in the workspace to assume that they are to be consumed directly:

    external_data_group(
        name = "meshes_nondevel",
        files = get_original_files(
            glob(['**/*.obj.sha512'])
        ),
        files_devel = glob(['**/*.obj']),
    )

This means that Bazel will automatically switch to using your local file, rather than use its own internal version. *Please use caution* when updating your branches.

## Extract Archives in Bazel `BUILD` Files

To unpack archives in Bazel `BUILD` files, first upload your archive (presently,
only `*.tar.gz` files.

Next, using the CLI tool, tell it to explicitly generate the manifest file when
you upload the file:

    ../tools/external_data/cli upload --manifest_generation=always archive.tar.gz

You should now see `archive.tar.gz.manifest.bzl`. Once this file is generated,
the manifest will by default be regenerated when you re-upload the archive.

In the `BUILD` file, you should now load this file, and pass it to
`extract_archive`:

    load("//tools:external_data.bzl",
        "external_data",
        "extract_archive",
    )
    load(":archive.tar.gz.manifest.bzl", archive_manifest="manifest")
    extract_archive(
        name = "archive",
        manifest = archive_manifest,
    )

Now you can use the `:archive` target as filegroup. For more information on usage, see
the function documentation for `extract_archive`.

## Download a Set of Files

If you wish to download *all* files of a given extension at the specified revision under a certain directory, you may use `find`. For example:

    find . -name '*.obj.sha512' | ./tools/external_data/cli download

For each `${file}.sha512` that is found, the file will be downloaded to `${file}`.

NOTE: This will fail if one of the outputs already exists; you must specify `--force` to enable overwriting.

As above, these files are cached.


## Download One File to a Specific Location

This is used in Bazel via `macros.bzl`:

    ./tools/external_data/cli download ${file}.sha512 --output ${file}


## Download Files and Expose as Symlinks (No Copy)

If you just need easy read-only access to files (and don't want to deal with Bazel's paths), you can use `--symlink`:

    ./tools/external_data/cli download --symlink *.sha512


## Integrity Checks

Note that just downloading the files may not check if the file is still available on the remote.
If you wish to ensure that other users can reproduce your results, consider `check`'ing your files:

    find . -name '*.sha512' | xargs ./tools/external_data/cli check

This will ensure that the correct file is stored on the remote, regardless of what is stored in the cache.

You may run these tests in Bazel:

    bazel test --test_tag_filters=external_data_check_test ...

This will check all external data tests in the current package and its subpackages.

*   Warning: All `external_data` tests are marked as `external`, thus the Bazel test results won't be cached, and the test (potentially downloading and checking a file) will *always* be run. Consider excluding this from tests that are normally run.
