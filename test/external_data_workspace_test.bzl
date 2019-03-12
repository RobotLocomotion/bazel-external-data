load(
    "//:expose_all_files.bzl",
    "recursive_filegroup",
)
load(
    "//test:workspace_test.bzl",
    "ARGS_DEFAULT",
    "workspace_test",
)

_workspace_list = [
    "external_data_pkg_test",
]

_upstream_files = [
    "//:all_files_recursive",
]

def external_data_workspace_test(
        name,
        workspace = None,
        args = ARGS_DEFAULT,
        data = []):
    """
    Convenience wrapper for `workspace_test`, specific to `external_data`
    tests.

    @param args See `workspace_test`.
    @param data
        See `workspace_test`. This test will automatically
        include basic upstream files from Drake (`//`) and
        the workspace test's files.
    """
    if workspace == None:
        workspace = name
    package = "@{}//".format(workspace)
    package_files = package + ":all_files_recursive"
    package_relpath = "external/" + workspace
    script = "external_data_workspace_test.sh"
    workspace_test(
        name = name,
        args = [
            "$(location {})".format(script),
            package_relpath,
        ] + args,
        data = [
            package_files,
            script,
        ] + _upstream_files + data,
    )

def collect_external_data_lint_files():
    """
    Creates a recursive_filegroup "all_${type}_files", where `type` will be
    all of {"bazel_lint", "python_lint"}, such that they can be consumed by
    `add_lint_tests` as extra files.
    """
    packages = ["//"]
    for workspace in _workspace_list:
        package = "@" + workspace + "//"

        # Prepare to expose all files recursively.
        packages.append(package)

    # Join files for linting, to permit $(locations ...) expansion directly
    # on transitive file dependencies.
    for name in ["bazel_lint_files", "python_lint_files"]:
        data = [package + ":" + name + "_recursive" for package in packages]
        recursive_filegroup(
            name = "all_" + name,
            data = data,
        )

def add_external_data_test_repositories(workspace_dir):
    """
    Adds test workspace directories as repositories so that their files can be
    consumed and their tests can be ignored by `bazel test ...` from Drake.
    """

    # WARNING: Bazel also craps out here if `workspace_dir + path` is used
    # rather than just `path`.
    # N.B. This error is *stateful*. You will get different behavior depending
    # on what has been built / run previously in Bazel. In one mode, the error
    # will be:
    #   Encountered error while [...]
    #   /home/${USER}/.cache/bazel/_bazel_${USER}/${HASH}/external/external_data_pkg_test  # noqa
    #   must  be an existing directory
    # In another mode, you will get Java errors:
    #   java.lang.IllegalArgumentException: PathFragment
    #   /workspace is not beneath
    #   /home/${USER}/${WORKSPACE_DIR}//workspace
    for workspace in _workspace_list:
        native.local_repository(
            name = workspace,
            path = "test/" + workspace,
        )
