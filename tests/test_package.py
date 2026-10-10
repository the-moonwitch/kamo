from importlib.metadata import version
from subprocess import run
from sys import executable
from typing import assert_type

import kamokamo


def test_version() -> None:
    assert_type(kamokamo.__version__, str)
    assert kamokamo.__version__ == version("kamokamo")


def test_import_defers_metadata_until_version_is_requested() -> None:
    run(
        [
            executable,
            "-c",
            """
import sys
import kamokamo

assert "importlib.metadata" not in sys.modules
assert "__version__" not in kamokamo.__dict__
assert not hasattr(kamokamo, "unknown_attribute")
assert "importlib.metadata" not in sys.modules

from kamokamo import __version__
from importlib.metadata import version

assert __version__ == version("kamokamo")
assert kamokamo.__dict__["__version__"] is __version__
assert kamokamo.__version__ is __version__
assert set(kamokamo.__all__) <= set(kamokamo.__dict__)
""",
        ],
        check=True,
    )
