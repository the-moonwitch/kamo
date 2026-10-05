from importlib.metadata import version

import kamo


def test_version() -> None:
    assert kamo.__version__ == version("kamo")
