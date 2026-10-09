"""typed functional vocabulary for Python."""

from importlib.metadata import version

from kamo.option import Nothing, NothingType, Option, Some, from_optional
from kamo.result import Err, Ok, Result

__version__: str = version("kamo")

__all__ = [
    "Err",
    "Nothing",
    "NothingType",
    "Ok",
    "Option",
    "Result",
    "Some",
    "__version__",
    "from_optional",
]
