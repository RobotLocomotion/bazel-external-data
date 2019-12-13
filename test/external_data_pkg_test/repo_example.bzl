load(
    "//tools:external_data.bzl",
    "external_data_repository_attrs",
    "external_data_repository_download",
)

_BUILD = """\
filegroup(
    name = "data",
    srcs = glob(["**/*.bin"]),
    visibility = ["//visibility:public"],
)
"""

def _impl(repo_ctx):
    # Download using external_data.
    archive_relpath = "data/archive.tar.gz"
    repo_ctx.symlink(
        Label("@external_data_pkg_test//data:archive.tar.gz.sha512"),
        archive_relpath + ".sha512",
    )
    external_data_repository_download(repo_ctx, [archive_relpath])

    repo_ctx.extract(
        archive_relpath,
        stripPrefix = "archive/",
        output="test_data/",
    )

    repo_ctx.file("BUILD.bazel", content=_BUILD)

_repo = repository_rule(
    implementation = _impl,
    local = True,
    attrs = external_data_repository_attrs(),
)

def add_repo_archive_repository(name = "repo_archive"):
    _repo(name = name)
