SETTINGS_DEFAULT = dict(
    # Warn if in development mode (e.g. if files will be lost when pushing).
    enable_warn = True,
    # Verbosity: Will dump configuration, including user information (e.g. API
    # keys!).
    verbose = False,
    # Label for sentinel file. Used to detect the project root.
    # To use `external_data_repository_download`, this must be a concrete source
    # file, and not NOT a filegroup target / genrule output.
    # WARNING: The sentinel MUST be placed next to the workspace root.
    # TODO(eric.cousineau): Simplify logic and relax this.
    cli_sentinel = "//:external_data_sentinel",
    # (Optional) Label for user configuration file. Namely for mock testing.
    # To use `external_data_repository_download`, this must be a concrete source
    # file, and not NOT a filegroup target / genrule output.
    cli_user_config = None,
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
_MANIFEST_SUFFIX = ".manifest.bzl"

def _get_cli_base_args(settings):
    args = []

    # Argument: Verbosity.
    if settings["verbose"]:
        args.append("--verbose")

    # Argument: Project root. Guess from the sentinel file rather than PWD, so
    # that a file could consumed by a downstream Bazel project.
    # (Otherwise, PWD will point to downstream project, which will make a
    # conflict.)
    args.append("--project_root_guess=$(location {})"
        .format(settings["cli_sentinel"]))

    # Extra Arguments (for project settings).
    cli_user_config = settings["cli_user_config"]
    if cli_user_config != None:
        args += ["--user_config=$(location {})".format(cli_user_config)]
    return args

def _get_cli_data(settings):
    data = [settings["cli_sentinel"]]
    cli_user_config = settings["cli_user_config"]
    if cli_user_config != None:
        data.append(cli_user_config)
    return data

def _add_dict(a, b):
    c = dict(a)
    c.update(b)
    return c

def external_data(
        file,
        mode = "normal",
        settings = SETTINGS_DEFAULT,
        tags = [],
        executable = False,
        visibility = None):
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
    @param executable
        If target should be executable.
    """

    # Overlay.
    # TODO: Check for invalid settings?
    settings = _add_dict(SETTINGS_DEFAULT, settings)

    if mode == "devel":
        # TODO(eric.cousineau): It'd be nice if there is a way to (a) check if
        # there is a `*.sha512` file, and if so, (b) check the hash of the
        # input file.
        if settings["enable_warn"]:
            # TODO(eric.cousineau): Print full location of given file?
            print("\nexternal_data(file = '{}', mode = 'devel'):".format(file) +
                  "\n  Using local workspace file in development mode." +
                  "\n  Please upload this file and commit the *{} file."
                      .format(_HASH_SUFFIX))
        native.exports_files(
            srcs = [file],
            visibility = visibility,
        )
    elif mode in ["normal", "no_cache"]:
        name = file + _RULE_SUFFIX
        hash_file = file + _HASH_SUFFIX

        # Binary:
        args = ["$(location {})".format(_TOOL)]

        # General commands.
        args += _get_cli_base_args(settings)

        # Subcommand: Download.
        args.append("download")

        # Argument: Caching.
        if mode == "no_cache":
            args.append("--no_cache")
            if executable:
                args.append("--executable")
        else:
            # Use symlinking to avoid needing to copy data to sandboxes.
            # The cache files are made read-only, so even if a test is run
            # with `--spawn_strategy=standalone`, there should be a permission
            # error when attempting to write to the file.
            if not executable:
                args.append("--symlink")
            else:
                args.append("--executable")

        # Argument: Hash file.
        args.append("$(location {})".format(hash_file))

        # Argument: Output file.
        args.append("--output=$@")

        cmd = " ".join(args)

        if settings["verbose"]:
            print("\nexternal_data(file = '{}', mode = '{}'):"
                .format(file, mode) + "\n  cmd: {}".format(cmd))

        data = _get_cli_data(settings) + [hash_file]

        native.genrule(
            name = name,
            srcs = data,
            outs = [file],
            cmd = cmd,
            tools = [_TOOL],
            tags = tags + [_RULE_TAG],
            # Changes `execroot`, and symlinks the files that we need to crawl
            # the directory structure and get hierarchical packages.
            local = 1,
            visibility = visibility,
        )

        if settings["enable_check_test"]:
            # Add test.
            external_data_check_test(
                name = file + _TEST_SUFFIX,
                files = [file],
                settings = settings,
                tags = [],
                visibility = visibility,
            )
    else:
        fail("Invalid mode: {}".format(mode))

def external_data_group(
        name,
        files,
        files_devel = [],
        mode = "normal",
        tags = [],
        settings = SETTINGS_DEFAULT,
        visibility = None):
    """Defines a group of external data files. """

    # Overlay.
    settings = _add_dict(SETTINGS_DEFAULT, settings)

    if settings["enable_warn"] and files_devel and mode == "devel":
        print("WARNING: You are specifying `files_devel` and " +
              '`mode="devel"`, which is redundant. Try choosing one.')

    kwargs = dict(
        visibility = visibility,
        tags = tags,
        settings = settings,
    )

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
    if settings["enable_warn"] and devel_only:
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
        tags = tags,
        visibility = visibility,
    )

def external_data_check_test(
        name,
        files,
        settings,
        tags = ["check_only"],
        **kwargs):
    """
    Checks that the given files are available on the remote (ignoring cache).

    By default, this is included by `external_data`. If this is not used
    through `external_data`, then the "no_build" tag will appear by default.
    """
    settings = _add_dict(SETTINGS_DEFAULT, settings)

    hash_files = [x + _HASH_SUFFIX for x in files]

    args = _get_cli_base_args(settings)
    args += ["check"] + ["$(location {})".format(x) for x in hash_files]

    # Use `exec.sh` to forward the existing CLI as a test.
    # TODO(eric.cousineau): Consider removing "external" as a test tag if it's
    # too cumbersome for general testing.
    native.sh_test(
        name = name,
        data = [_TOOL] + _get_cli_data(settings) + hash_files,
        srcs = ["@bazel_external_data_pkg//:exec.sh"],
        args = ["$(location {})".format(_TOOL)] + args,
        tags = tags + _TEST_TAGS + ["external"],
        # Changes `execroot`, and symlinks the files that we need to crawl the
        # directory structure and get hierarchical packages.
        local = 1,
        **kwargs
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

def _get_common_output_dir(attrs, outputs):
    """Helper for extract_archive().  Returns the single output_dir that is
    shared by all outputs, given the package-relate attr paths for those
    outputs.  This is used to populate --output_dir for extract_archive.py.
    The result does not contain a trailing "/".
    """
    (len(attrs) == len(outputs)) or fail("Mismatched lengths")
    output_dirs = []
    for i in range(len(attrs)):
        output_path = outputs[i].path
        name_within_package = attrs[i].name
        expected_path_suffix = "/" + name_within_package
        if not output_path.endswith(expected_path_suffix):
            fail("Could not strip {} from {} path".format(
                name_within_package, output_path))
        output_dir = output_path[:-len(expected_path_suffix)]
        if output_dir not in output_dirs:
            output_dirs.append(output_dir)
    if len(output_dirs) != 1:
        fail("Could not identify unique output_dir in {}".format(
            output_dirs))
    return output_dirs[0]

def _extract_archive_impl(ctx):
    """The helper rule implementation for extract_archive(), below."""
    output_root = _get_common_output_dir(ctx.attr.outs, ctx.outputs.outs)
    args = ctx.actions.args()
    args.add(ctx.file.archive)
    args.add("--manifest", ctx.file.manifest)
    if ctx.attr.output_dir:
        args.add("--output_dir", output_root + "/" + ctx.attr.output_dir)
    else:
        args.add("--output_dir", output_root)
    args.add("--strip_prefix", ctx.attr.strip_prefix)
    ctx.actions.run(
        executable = ctx.executable.tool,
        tools = [ctx.executable.tool],
        inputs = [ctx.file.archive, ctx.file.manifest],
        outputs = ctx.outputs.outs,
        arguments = [args],
        mnemonic = "Extract",
        progress_message = "Extracting {}".format(
            ctx.file.archive.basename,
        ),
    )

# The helper rule declaration for extract_archive(), below.
_extract_archive_rule = rule(
    attrs = {
        "tool": attr.label(
            default = "@bazel_external_data_pkg//:extract_archive",
            executable = True,
            cfg = "host",
        ),
        "archive": attr.label(allow_single_file = True, mandatory = True),
        "manifest": attr.label(allow_single_file = True, mandatory = True),
        "strip_prefix": attr.string(),
        "output_dir": attr.string(),
        "outs": attr.output_list(mandatory = True)
    },
    implementation = _extract_archive_impl,
)

def extract_archive(
        name,
        manifest,
        archive = None,
        strip_prefix = "",
        output_dir = "",
        tags = None,
        visibility = None):
    """Extracts an archive into a Bazel genfiles tree.

    Example:
        load(
            "//tools/external_data:macros.bzl",
            "extract_archive",
        )
        load(":my_archive.tar.gz.manifest.bzl", my_archive_manifest="manifest")
        extract_archive(
            name = "my_archive",
            archive = "my_archive.tar.gz",
            manifest = my_archive_manifest,
            strip_prefix = "my_archive/",
            output_dir = "other_dir",
        )

    @param manifest
        Manifest dictionary loaded from a manifest Bazel file.
        Due to constraints in Bazel, we must load this file. For simplicity,
        this file must be named "{archive}.manifest.bzl".
    @param archive
        Archive to be extracted. If not supplied, will be "{name}.tar.gz".
    @param strip_prefix
        Prefix to be stripped from archive. If non-empty, must end with `/`.
    @param output_dir
        Output directory. If non-empty, must not end with `/`.
    """

    # Using: https://groups.google.com/forum/#!topic/bazel-discuss/B5WFlG3co4I
    # TODO(eric.cousineau): Add ability to select specific files of the archive
    # with globs or something (after stripping prefix).
    if archive == None:
        archive = name + ".tar.gz"
    if manifest == None:
        fail("Manifest must be supplied")
    if output_dir.endswith("/"):
        fail("`output_dir` must not end with `/`")
    if strip_prefix and not strip_prefix.endswith("/"):
        fail("`strip_prefix` must end with `/` if non-empty")
    outs = []
    for file in manifest["files"]:
        if file.startswith(strip_prefix):
            out = file[len(strip_prefix):]
            if output_dir:
                out = output_dir + "/" + out
            outs.append(out)
    if len(outs) == 0:
        fail(("archive: There are no outputs, and empty genrule's are " +
              "invalid.\n" +
              "  After `strip_prefix` filtering, there were no outputs, but " +
              "there were {} original files. Did you use the wrong prefix?")
            .format(len(manifest["files"])))
    _extract_archive_rule(
        name = name + ".extract_archive_rule",
        archive = archive,
        manifest = archive + _MANIFEST_SUFFIX,
        strip_prefix = strip_prefix,
        output_dir = output_dir,
        outs = outs,
        tags = [
            # Only run the extract_archive_rule when its files are needed;
            # do not run it as part of `bazel build //...`.
            "manual",
        ],
        visibility = ["//visibility:private"],
    )
    native.filegroup(
        name = name,
        srcs = outs,
        tags = tags,
        visibility = visibility,
    )

def external_data_repository_attrs(settings=SETTINGS_DEFAULT):
    """
    Attributes necessary for `external_data_repository_download()`.
    """
    settings = _add_dict(SETTINGS_DEFAULT, settings)
    # NOTE: all these labels are listed as private attributes to force prefetching, or else
    # repository rules will be restarted on first hit.
    # See https://github.com/bazelbuild/bazel/commit/cdc99afc1a03ff8fbbbae088d358b7c029e0d232
    # and https://github.com/bazelbuild/bazel/issues/4533 for further reference.
    return {
        "_cli_sentinel": attr.label(default = settings["cli_sentinel"]),
        "_cli_user_config": attr.label(default = settings["cli_user_config"]),
        "_proxy_script": attr.label(default = "@bazel_external_data_pkg//:.external_data_cli_proxy.py"),
    }


def external_data_repository_download(
        repo_ctx,
        files,
        settings=SETTINGS_DEFAULT,
        python_bin="/usr/bin/python3"):
    """
    Provides a mechanism to download external data files as part of a
    repository rule.

    Requires `external_data_repository_attrs()` to have been included in
    `repository_rule(*, attrs)`.

    Arguments:
        files: Relative paths (to this repository's root) of files to download.
        settings: Project-specific overrides to SETTINGS_DEFAULT.
        python_bin: Path to Python binary.

    Example:

        def _add_my_repo_impl(repo_ctx):
            ...
            external_data_repository_download(repo_ctx, [archive_relpath])
            repo_ctx.extract(...)
            repo_ctx.file("BUILD.bazel", ...)

        _my_repo_attrs = {
            "my_repo_stuff": attr.thing(),
        }
        _my_repo_attrs.update(external_data_repository_attrs())

        add_my_repo = repository_rule(
            implementation = _add_my_repo_impl,
            local = True,
            attrs = _my_repo_attrs,
        )

    """
    settings = _add_dict(SETTINGS_DEFAULT, settings)

    # For clean up later.
    files_to_remove = []

    # Add setup files.
    local_proxy_script = ".external_data_cli_proxy.py"
    # TODO(eric.cousineau): Symlink all relevant source files for more
    # robustness.
    repo_ctx.symlink(repo_ctx.attr._proxy_script, local_proxy_script)
    files_to_remove.append(local_proxy_script)

    args = [python_bin, local_proxy_script]
    if settings["verbose"]:
        args += ["--verbose"]

    # Inject config file so that we can read from it.
    local_sentinel = ".external_data.yml"
    repo_ctx.symlink(repo_ctx.attr._cli_sentinel, local_sentinel)
    files_to_remove.append(local_sentinel)
    args += ["--project_root_guess=" + local_sentinel]

    if repo_ctx.attr._cli_user_config != None:
        local_user_config = ".user_config.yml"
        repo_ctx.symlink(repo_ctx.attr._cli_user_config, local_user_config)
        files_to_remove.append(local_user_config)
        args += ["--user_config=" + local_user_config]

    # Download.
    args += ["download", "--symlink"] + files

    res = repo_ctx.execute(args)
    if res.return_code != 0:
        print("Executing command {}".format(args))
        fail("External data failure: {}\n{}".format(res.stdout, res.stderr))

    # Clean up.
    for file in files_to_remove:
       repo_ctx.delete(file)
