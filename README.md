# About

This is a Bazel-focused implementation for incorporating external data that is versioned (using a hash file rather than in Git) for testing and running binaries.

This design is based on Kitware's [CMake/ExternalData](https://blog.kitware.com/cmake-externaldata-using-large-files-with-distributed-version-control/) module, with the implementation based on [this demo repository](https://github.com/jcfr/bazel-large-files-with-girder).

## Documentation

Please see [`docs/README.md`](docs/README.md).
