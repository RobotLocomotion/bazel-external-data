# We will inject additional settings here.
load("@bazel_external_data_pkg//tools:macros.bzl",
    _external_data="external_data",
    _external_data_group="external_data_group",
    "get_original_files"
)

SETTINGS = dict(
    cli_sentinel = "//:external_data_sentinel",
    cli_data = [
        "//tools:external_data.user.yml",
    ],
    cli_extra_args = [
        "--project_name=bazel_pkg_advanced_test",
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
