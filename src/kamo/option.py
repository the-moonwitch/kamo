"""immutable optional values, with Rust-style combinators."""

from collections.abc import Callable, Iterable, Iterator
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from types import ClassMethodDescriptorType, GenericAlias, MemberDescriptorType
from typing import (
    ClassVar,
    Generic,
    Literal,
    Never,
    Self,
    TypeVar,
    cast,
    final,
    get_args,
    overload,
)

__all__ = ["Nothing", "Option", "Some", "from_optional"]

T = TypeVar("T", covariant=True)


@overload
def from_optional(value: None) -> _Nothing: ...


@overload
def from_optional[U](value: U | None) -> Option[U]: ...


def from_optional[U](value: U | None) -> Option[U]:
    """convert Python's None sentinel to Nothing."""
    return Nothing if value is None else Some(value)


# explicit covariance survives method aliases in all supported type checkers.
class _Option(Generic[T]):  # noqa: UP046
    __slots__ = ()

    def is_some_and(self, predicate: Callable[[T], bool]) -> bool:
        return False

    def is_none_or(self, predicate: Callable[[T], bool]) -> bool:
        return True

    def unwrap(self) -> T:
        """return the value, or raise ValueError for Nothing."""
        raise ValueError("called unwrap on Nothing")

    def expect(self, message: str) -> T:
        """return the value, or raise ValueError with the given message."""
        raise ValueError(message)

    def unwrap_or[U](self, default: U) -> T | U:
        return default

    def unwrap_or_else[U](self, default: Callable[[], U]) -> T | U:
        return default()

    def to_optional(self) -> T | None:
        """convert to Python's None sentinel."""
        return None

    def map[U](self, function: Callable[[T], U]) -> Option[U]:
        return Nothing

    def map_or[U, V](self, default: U, function: Callable[[T], V]) -> U | V:
        return default

    def map_or_else[U, V](
        self, default: Callable[[], U], function: Callable[[T], V]
    ) -> U | V:
        return default()

    def inspect(self, function: Callable[[T], object]) -> Self:
        """call function on a present value and return this option."""
        return self

    def and_[U](self, other: Option[U]) -> Option[U]:
        return Nothing

    def and_then[U](self, function: Callable[[T], Option[U]]) -> Option[U]:
        return Nothing

    def or_[U](self, other: Option[U]) -> Option[T | U]:
        return other

    def or_else[U](self, default: Callable[[], Option[U]]) -> Option[T | U]:
        return default()

    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        return Nothing

    def xor[U](self, other: Option[U]) -> Option[T | U]:
        return other

    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        return Nothing

    def zip_with[U, V](
        self, other: Option[U], function: Callable[[T, U], V]
    ) -> Option[V]:
        return Nothing

    def unzip[A, B](
        self: _Option[tuple[A, B]],
    ) -> tuple[Option[A], Option[B]]:
        return _nothing_pair

    def flatten[U](self: _Option[Option[U]]) -> Option[U]:
        return Nothing


@final
@dataclass(frozen=True, slots=True, repr=False)
class Some(_Option[T]):
    """a present value, including None and other falsey values."""

    value: T
    is_some: ClassVar[Literal[True]] = True
    is_none: ClassVar[Literal[False]] = False

    def __init__(self, value: T) -> None:
        _set_value(self, value)

    @classmethod
    def __class_getitem__(cls, parameters: object) -> GenericAlias:
        try:
            return _cached_alias(cls, parameters)
        except TypeError:
            # valid type arguments can have an unhashable metaclass.
            return _alias(cls, parameters)

    def __repr__(self) -> str:
        return f"Some({self.value!r})"

    def __copy__(self) -> Some[T]:
        return Some(self.value)

    def __deepcopy__(self, memo: dict[int, object]) -> Some[T]:
        result = object.__new__(type(self))
        # register before cloning the payload, which may refer to this option.
        memo[id(self)] = result
        _set_value(result, deepcopy(self.value, memo))
        return result

    def __getstate__(self) -> list[T]:
        return [self.value]

    def __setstate__(self, state: Iterable[object]) -> None:
        for value in state:
            _set_value(self, value)
            break

    def __iter__(self) -> Iterator[T]:
        """a fresh iterator over the present value."""
        return iter((self.value,))

    iter = __iter__

    def is_some_and(self, predicate: Callable[[T], bool]) -> bool:
        return predicate(self.value)

    def is_none_or(self, predicate: Callable[[T], bool]) -> bool:
        return predicate(self.value)

    def unwrap(self) -> T:
        return self.value

    def expect(self, message: str) -> T:
        return self.value

    def unwrap_or(self, default: object) -> T:
        return self.value

    def unwrap_or_else[U](self, default: Callable[[], U]) -> T:
        return self.value

    def to_optional(self) -> T:
        return self.value

    def map[U](self, function: Callable[[T], U]) -> Some[U]:
        return Some(function(self.value))

    def map_or[V](self, default: object, function: Callable[[T], V]) -> V:
        return function(self.value)

    def map_or_else[U, V](
        self, default: Callable[[], U], function: Callable[[T], V]
    ) -> V:
        return function(self.value)

    def inspect(self, function: Callable[[T], object]) -> Self:
        function(self.value)
        return self

    def and_[U](self, other: Option[U]) -> Option[U]:
        return other

    def and_then[U](self, function: Callable[[T], Option[U]]) -> Option[U]:
        return function(self.value)

    def or_[U](self, other: Option[U]) -> Self:
        return self

    def or_else[U](self, default: Callable[[], Option[U]]) -> Self:
        return self

    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        return self if predicate(self.value) else Nothing

    def xor[U](self, other: Option[U]) -> Option[T | U]:
        return Nothing if other.is_some else self

    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        return (
            Some((self.value, other.value))
            if other.is_some is True
            else Nothing
        )

    def zip_with[U, V](
        self, other: Option[U], function: Callable[[T, U], V]
    ) -> Option[V]:
        """combine present payloads without an intermediate pair."""
        return (
            Some(function(self.value, other.value))
            if other.is_some is True
            else Nothing
        )

    def unzip[A, B](
        self: Some[tuple[A, B]],
    ) -> tuple[Some[A], Some[B]]:
        first, second = self.value
        return Some(first), Some(second)

    def flatten[U](self: Some[Option[U]]) -> Option[U]:
        return self.value


# initialize the generated slot directly, retaining frozen dataclass semantics.
_set_value: Callable[[object, object], None] = cast(
    MemberDescriptorType, Some.__dict__["value"]
).__set__


class _SomeAlias(GenericAlias):
    __slots__ = ()
    # frozen options cannot store __orig_class__; skip that failed assignment.
    __call__ = Some

    def __getitem__(self, parameters: object) -> GenericAlias:
        specialized = super().__getitem__(parameters)
        return _SomeAlias(Some, specialized.__args__)


_generic_getitem = cast(
    ClassMethodDescriptorType, Generic.__dict__["__class_getitem__"]
)


def _alias(cls: type[object], parameters: object) -> GenericAlias:
    getitem = cast(
        "Callable[[object], object]", _generic_getitem.__get__(None, cls)
    )
    alias_type = _SomeAlias if cls is Some else GenericAlias
    return alias_type(cls, get_args(getitem(parameters)))


_cached_alias = cast(
    "Callable[[type[object], object], GenericAlias]",
    lru_cache(maxsize=128)(_alias),
)


@final
@dataclass(frozen=True, slots=True, repr=False)
class _Nothing(_Option[Never]):
    is_some: ClassVar[Literal[False]] = False
    is_none: ClassVar[Literal[True]] = True

    def __repr__(self) -> str:
        return "Nothing"

    # native constant hooks avoid Python frames and speculative list capacity.
    __bool__ = False.__bool__
    __iter__ = ().__iter__
    iter = __iter__
    __length_hint__ = ().__len__

    def __hash__(self) -> int:
        return _nothing_hash

    def __getstate__(self) -> list[object]:
        return []

    def __setstate__(self, state: Iterable[object]) -> None:
        return None

    def __copy__(self) -> Self:
        return type(self)()

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        return type(self)()


# a closed union preserves the payload type when matching either variant.
type Option[T] = Some[T] | _Nothing

Nothing = _Nothing()
_nothing_hash = hash(())
_nothing_pair = (Nothing, Nothing)
