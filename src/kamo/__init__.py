"""typed functional vocabulary for Python."""

from importlib.metadata import version

from kamo.option import Nothing, Option, Some, from_optional

__version__: str = version("kamo")

__all__ = ["Nothing", "Option", "Some", "__version__", "from_optional"]
