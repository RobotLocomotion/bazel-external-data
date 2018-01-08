SETTINGS_DEFAULT = dict(
    # Warn if in development mode (e.g. if files will be lost when pushing).
    enable_warn = True,
    # Verbosity: Will dump configuration, including user information (e.g. API
    # keys!).
    verbose = False,
    # Sentinel data. Used to detect the project root.
    # WARNING: The sentinel MUST be placed next to the workspace root.
    # TODO(eric.cousineau): If the logic can be simplified, consider relaxing
    # this.
    cli_sentinel = "//:external_data_sentinel",
    # Extra tool data. Generally, this is empty. However, any custom
    # configuration modules can be included here as well.
    cli_data = [],
    # Extra arguments to `cli`. Namely for `--user_config` for mock testing,
    # but can be changed.
    # @note This is NOT for arguments after `cli ... download`.
    cli_extra_args = [],
    # For each `external_data` target, will add an integrity check for the file.
    enable_check_test = True,
)


_HASH_SUFFIX = ".sha512"
_RULE_SUFFIX = "__download"
_RULE_TAG = "external_data"
_TEST_SUFFIX = "__check_test"
# @note This does NOT include 'external_data', so that running with
# --test_tag_filters=external_data does not require a remote.
_TEST_TAGS = ["external_data_check_test"]
_TOOL = "@bazel_external_data_pkg//:cli"


def _get_cli_base_args(filepath, settings):
    args = []
    # Argument: Verbosity.
    if settings['verbose']:
        args.append("--verbose")
    # Argument: Project root. Guess from the sentinel file rather than PWD, so
    # that a file could consumed by a downstream Bazel project.
    # (Otherwise, PWD will point to downstream project, which will make a
    # conflict.)
    args.append("--project_root_guess=$(location {})"
                .format(settings['cli_sentinel']))
    # Extra Arguments (for project settings).
    cli_extra_args = settings['cli_extra_args']
    if cli_extra_args:
        args += cli_extra_args
    return args


def external_data(
        file,
        mode='normal',
        settings=SETTINGS_DEFAULT,
        visibility=None):
    """Defines an external data file.

    @param file
        Name of the file to be downloaded.
    @param mode
        'normal' - Use cached file if possible. Otherwise download the file.
        'devel' - Use local workspace (for development).
        'no_cache' - Download the file, do not use the cache.
    @param settings
        Settings for target. See `SETTINGS_DEFAULT` for the each setting and
        its purpose.
    """
    # Overlay.
    # TODO: Check for invalid settings?
    settings = SETTINGS_DEFAULT + settings

    if mode == 'devel':
        # TODO(eric.cousineau): It'd be nice if there is a way to (a) check if
        # there is a `*.sha512` file, and if so, (b) check the hash of the
        # input file.
        if settings['enable_warn']:
            # TODO(eric.cousineau): Print full location of given file?
            print("\nexternal_data(file = '{}', mode = 'devel'):".format(file) +
                  "\n  Using local workspace file in development mode." +
                  "\n  Please upload this file and commit the *{} file."
                  .format(_HASH_SUFFIX))
        native.exports_files(
            srcs = [file],
            visibility = visibility,
        )
    elif mode in ['normal', 'no_cache']:
        name = file + _RULE_SUFFIX
        hash_file = file + _HASH_SUFFIX

        # Binary:
        args = ["$(location {})".format(_TOOL)]
        # General commands.
        args += _get_cli_base_args(hash_file, settings)
        # Subcommand: Download.
        args.append("download")
        # Argument: Caching.
        if mode == 'no_cache':
            args.append("--no_cache")
        else:
            # Use symlinking to avoid needing to copy data to sandboxes.
            # The cache files are made read-only, so even if a test is run
            # with `--spawn_strategy=standalone`, there should be a permission
            # error when attempting to write to the file.
            args.append("--symlink")
        # Argument: Hash file.
        args.append("$(location {})".format(hash_file))
        # Argument: Output file.
        args.append("--output=$@")

        cmd = " ".join(args)

        if settings['verbose']:
            print("\nexternal_data(file = '{}', mode = '{}'):"
                  .format(file, mode) + "\n  cmd: {}".format(cmd))

        cli_sentinel = settings['cli_sentinel']
        cli_data = settings['cli_data']
        data = [hash_file, cli_sentinel] + cli_data

        native.genrule(
            name = name,
            srcs = data,
            outs = [file],
            cmd = cmd,
            tools = [_TOOL],
            tags = [_RULE_TAG],
            # Changes `execroot`, and symlinks the files that we need to crawl
            # the directory structure and get hierarchical packages.
            local = 1,
            visibility = visibility,
        )

        if settings['enable_check_test']:
            # Add test.
            _external_data_check_test(file, settings)
    else:
        fail("Invalid mode: {}".format(mode))


def external_data_group(
        name,
        files,
        files_devel = [],
        mode='normal',
        settings=SETTINGS_DEFAULT,
        visibility=None):
    """Defines a group of external data files. """

    # Overlay.
    settings = SETTINGS_DEFAULT + settings

    if settings['enable_warn'] and files_devel and mode == "devel":
        print('WARNING: You are specifying `files_devel` and ' +
              '`mode="devel"`, which is redundant. Try choosing one.')

    kwargs = {'visibility': visibility, 'settings': settings}

    for file in files:
        if file not in files_devel:
            external_data(file, mode, **kwargs)
        else:
            external_data(file, "devel", **kwargs)

    # Consume leftover `files_devel`.
    devel_only = []
    for file in files_devel:
        if file not in files:
            devel_only.append(file)
            external_data(file, "devel", **kwargs)
    if settings['enable_warn'] and devel_only:
        print("""
WARNING: The following `files_devel` files are not in `files`:\n" +
    {}
  If you remove `files_devel`, then these files will not be part of the
  target.
  If you are using a `glob`, they may not have a corresponding *{}
  file.""".format("\n    ".join(devel_only), _HASH_SUFFIX))

    all_files = files + devel_only
    native.filegroup(
        name = name,
        srcs = all_files,
    )


def _external_data_check_test(file, settings):
    # This test merely checks that this file is indeed available on the remote
    # (ignoring cache).
    name = file + _TEST_SUFFIX
    hash_file = file + _HASH_SUFFIX

    args = _get_cli_base_args(hash_file, settings)
    args += [
        "check",
        "$(location {})".format(hash_file),
    ]

    cli_sentinel = settings['cli_sentinel']
    cli_data = settings['cli_data']

    # TODO(eric.cousineau): Consider removing "external" as a test tag if it's
    # too cumbersome for general testing.

    # Have to use `py_test` to run an existing binary with arguments...
    # Blech.
    native.py_test(
        name = name,
        data = [hash_file, cli_sentinel] + cli_data,
        srcs = [_TOOL],
        main = _TOOL + ".py",
        deps = ["@bazel_external_data_pkg//:cli_deps"],
        args = args,
        tags = _TEST_TAGS + ["external"],
        # Changes `execroot`, and symlinks the files that we need to crawl the
        # directory structure and get hierarchical packages.
        local = 1,
    )
    return name


def get_original_files(hash_files):
    """Gets the original file from a given hash file. """
    files = []
    for hash_file in hash_files:
        if not hash_file.endswith(_HASH_SUFFIX):
            fail("Hash file does end with '{}': '{}'"
                 .format(_HASH_SUFFIX, hash_file))
        file = hash_file[:-len(_HASH_SUFFIX)]
        files.append(file)
    return files
