from importlib.metadata import version
from subprocess import run
from sys import executable
from typing import assert_type

import kamo


def test_version() -> None:
    assert_type(kamo.__version__, str)
    assert kamo.__version__ == version("kamo")


def test_import_defers_metadata_until_version_is_requested() -> None:
    run(
        [
            executable,
            "-c",
            """
import sys
import kamo

assert "importlib.metadata" not in sys.modules
assert "__version__" not in kamo.__dict__
assert not hasattr(kamo, "unknown_attribute")
assert "importlib.metadata" not in sys.modules

from kamo import __version__
from importlib.metadata import version

assert __version__ == version("kamo")
assert kamo.__dict__["__version__"] is __version__
assert kamo.__version__ is __version__
assert set(kamo.__all__) <= set(kamo.__dict__)
""",
        ],
        check=True,
    )
