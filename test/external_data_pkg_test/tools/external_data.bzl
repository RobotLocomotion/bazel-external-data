# Pass through.
load(
    "@bazel_external_data_pkg//:external_data.bzl",
    "extract_archive",
    "get_original_files",
    _external_data = "external_data",
    _external_data_check_test = "external_data_check_test",
    _external_data_group = "external_data_group",
)

SETTINGS = dict(
    cli_sentinel = "//:external_data_sentinel",
    cli_data = [
        "//tools:external_data.user.yml",
    ],
    cli_extra_args = [
        "--user_config=$(location //tools:external_data.user.yml)",
    ],
)

def external_data(*args, **kwargs):
    _external_data(
        settings = SETTINGS,
        *args,
        **kwargs
    )

def external_data_group(*args, **kwargs):
    _external_data_group(
        settings = SETTINGS,
        *args,
        **kwargs
    )

def external_data_check_test(*args, **kwargs):
    _external_data_check_test(
        settings = SETTINGS,
        *args,
        **kwargs
    )
