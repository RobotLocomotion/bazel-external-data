from bazel_external_data.backends.mock import MockBackend
from bazel_external_data.backends.girder import GirderHashsumBackend
from bazel_external_data.backends.s3 import S3Backend


def get_default_backends():
    """ Get all available backends provided via `bazel_external_data`. """
    backends = {
        "mock": MockBackend,
        "girder_hashsum": GirderHashsumBackend,
        "s3": S3Backend,
    }
    return backends
