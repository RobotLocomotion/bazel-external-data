# Setup

## Prerequisites

For a basic client, you must base `python` and the `girder_client` installed.

Please see [`client_prereqs.sh`](../test/backends/girder/docker/client_prereqs.sh) for `apt` packages.

**NOTE**: This is a subset of Drake's `install_prereqs.sh`.

### Backends

#### Girder

You can download files from Girder using the nominal prerequisites.

However, if you wish to upload, you must have `girder_client` on your system. You may install this via `pip`:

    pip install girder-client

Consider using `virtualenv --system-site-packages` to try out `girder_client`:

    env_dir=/path/to/directory
    virtualenv --system-site-packages ${env_dir}
    source ${env_dir}/bin/activate
    pip install girder-client

**NOTE**: Ensure that you are using this environment when using the CLI!

## Configuration

* Inspect the configuration examples in `docs/config`:
    * `external_data.user.yml` - Copy this to `~/.config/bazel_external_data/config.yml`
        * User configuration: global cache, backend-specific authentication (if they don't have their won caching) - NOT to be versioned!
        * Default values will be used if this file does not exist or define them.
    * `external_data.project.yml` - Goes to `${workspace_dir}/.external_data.project.yml`
        * Project configuration.
    * `external_data.package.yml` - Goes to `${package_dir}/.external_data.yml`
        * Package configuration.
        * You will need one adjacent to the project configuration. You may have others in subdirectories.
