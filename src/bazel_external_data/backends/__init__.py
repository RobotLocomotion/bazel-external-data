from bazel_external_data.backends.mock import MockBackend


def get_default_backends():
    """ Get all available backends provided via `bazel_external_data`. """
    backends = {
        "mock": MockBackend,
    }
    return backends
