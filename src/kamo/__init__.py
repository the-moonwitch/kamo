"""typed functional vocabulary for Python."""

from typing import TYPE_CHECKING

from kamo.iter import Iter, Peekable
from kamo.option import Nothing, NothingType, Option, Some, from_optional
from kamo.result import Err, Ok, Result

__version__: str

if not TYPE_CHECKING:

    def __getattr__(name: str) -> str:
        if name != "__version__":
            raise AttributeError(
                f"module {__name__!r} has no attribute {name!r}"
            )
        from importlib.metadata import version

        value = version("kamo")
        globals()[name] = value
        return value


__all__ = [
    "Err",
    "Iter",
    "Nothing",
    "NothingType",
    "Ok",
    "Option",
    "Peekable",
    "Result",
    "Some",
    "__version__",
    "from_optional",
]
