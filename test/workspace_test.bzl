# -*- python -*-

# Include release options:
# https://docs.bazel.build/versions/master/user-manual.html#bazel-releng
ARGS_DEFAULT = [
    "bazel",
    "--nohome_rc",
    "--batch",
    "test",
    "--announce_rc",
     "--test_output=errors",
     "--test_summary=terse",
    "//...",
]

def workspace_test(
        name,
        args = ARGS_DEFAULT,
        data = []):
    """
    Copies all contents under `*.runfiles/${workspace}/**` to a temporary
    directory, then evalutates `args` in `bash` in the new temporary runfiles
    workspace directory.

    @param args
        Arguments for `bash` to execute. By default, will run
        `bazel test //...` with release flavoring.
    @param data
        Data required for the workspace test.
    """
    native.sh_test(
        name = name,
        srcs = ["@bazel_external_data_pkg//test:workspace_test.sh"],
        args = args,
        data = data,
    )
