load(
    "//tools:external_data.bzl",
    "external_data_repository_attrs",
    "external_data_repository_download",
)

def _impl(repo_ctx):
    # Download using external_data.
    archive_relpath = "data/archive.tar.gz"
    repo_ctx.symlink(
        Label("@external_data_pkg_test//data:archive.tar.gz.sha512"),
        archive_relpath + ".sha512",
    )
    external_data_repository_download(repo_ctx, [archive_relpath])

    # Use the `extract` functionality from `download_and_extract`.
    # N.B. This will complain about not having a SHA256. Consider just using
    # `tar` or direct command line?
    repo_ctx.download_and_extract(
        "file://{}".format(repo_ctx.path(archive_relpath)),
        stripPrefix = "archive/",
        output="test_data/",
    )

    repo_ctx.file("BUILD.bazel", content="""
filegroup(
    name = "data",
    srcs = glob(["**/*.bin"]),
    visibility = ["//visibility:public"],
)
""")

_repo = repository_rule(
    implementation = _impl,
    local = True,
    attrs = external_data_repository_attrs(),
)

def add_repo_archive_repository(name = "repo_archive"):
    _repo(name = name)
