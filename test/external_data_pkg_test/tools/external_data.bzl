# Pass through.
load("@bazel_external_data_pkg//:external_data.bzl",
    _external_data="external_data",
    _external_data_group="external_data_group",
    "get_original_files",
    "extract_archive",
)

SETTINGS = dict(
    cli_sentinel = "//:external_data_sentinel",
    cli_data = [
        "//tools:external_data.user.yml",
    ],
    cli_extra_args = [
        "--user_config=$(location //tools:external_data.user.yml)"
    ],
)


def external_data(*args, **kwargs):
    _external_data(
        *args,
        settings = SETTINGS,
        **kwargs
    )


def external_data_group(*args, **kwargs):
    _external_data_group(
        *args,
        settings = SETTINGS,
        **kwargs
    )
