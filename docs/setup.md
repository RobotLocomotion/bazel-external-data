# Setup

## Prerequisites

For a basic client, you must have `python3` installed.

If you wish to upload files to Girder, have `girder_client` installed.
For example:

    pip install --user girder_client

## Configuration

* Inspect the configuration examples in `docs/config`:
    * `external_data.user.yml` - Copy this to `~/.config/bazel_external_data/config.yml`
        * User configuration: global cache, backend-specific authentication (if they don't have their won caching) - NOT to be versioned!
        * **Note**: This file is not necessary if you wish to use the default cache directory and do not need any backend-specific authentication.
    * `external_data.project.yml` - Goes to `${workspace_dir}/.external_data.yml`
        * Project configuration.
