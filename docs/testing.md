# Testing

Relevant workflow tests are located in `test/`.

To run *all* tests, execute `test/run_tests.sh`.

General tests, under `test/...`:

* `workflows_test.sh` - Tests general workflows (covered in [Workflows](./workflows.md), using `bazel_pkg_advanced_test`.
* `bazel_pkg_test` - An very simple example Bazel package which consumes `bazel_external_data` (via `local_repository`).
    * *WARNING*: The remote is configured for a single file for simplicity. Consider replacing this.
* `bazel_pkg_downstream_test` - A Bazel package that consumes `bazel_pkg_test`, and can access its files that are generated from `external_data`.
* `bazel_pkg_advanced_test` - Extended example, which uses custom configurations for (a) user config, (b) Bazel config (`settings`), and (c) setup conig (`external_data_config.py`).
    * This has Mock storage mechanisms with persistent upload directories (located in `/tmp`.
