# Can't name it `bazel_external_data` due to Python package clashes.
# @ref https://github.com/bazelbuild/bazel/issues/3998
workspace(name = "bazel_external_data_pkg")

# Include these as local repositories to have them be ignored by `test ...`.
# @ref https://github.com/bazelbuild/bazel/issues/2460#issuecomment-296940882
local_repository(
    name = "bazel_external_data_test_ignore",
    path = "test/workspaces",
)

# TODO: Can externals' tests be aliased into an existing repo?
# (e.g. can Drake alias these tests for the time being?)
