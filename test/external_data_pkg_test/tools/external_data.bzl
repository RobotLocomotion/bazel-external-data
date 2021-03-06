# Pass through.
load(
    "@bazel_external_data_pkg//:external_data.bzl",
    _extract_archive = "extract_archive",
    _get_original_files = "get_original_files",
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

def extract_archive(*args, **kwargs):
    _extract_archive(*args, **kwargs)

def get_original_files(*args, **kwargs):
    return _get_original_files(*args, **kwargs)

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
