# Can't name it `bazel_external_data` due to Python package clashes.
# @ref https://github.com/bazelbuild/bazel/issues/3998
workspace(name = "bazel_external_data_pkg")

load("//test:external_data_workspace_test.bzl", "add_external_data_test_repositories")

add_external_data_test_repositories(__workspace_dir__)
