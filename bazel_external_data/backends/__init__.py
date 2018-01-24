from bazel_external_data.backends.mock import MockBackend
from bazel_external_data.backends.girder import GirderHashsumBackend


def get_default_backends():
    """ Get all available backends provided via `bazel_external_data`. """
    backends = {
        "mock": MockBackend,
        "girder_hashsum": GirderHashsumBackend,
    }
    return backends
