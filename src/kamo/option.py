"""immutable optional values, with Rust-style combinators."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import MemberDescriptorType
from typing import Never, Self, TypeVar, cast, final, overload

__all__ = ["Nothing", "Option", "Some", "from_optional"]

T = TypeVar("T", covariant=True)


@overload
def from_optional(value: None) -> _Nothing: ...


@overload
def from_optional[U](value: U | None) -> Option[U]: ...


def from_optional[U](value: U | None) -> Option[U]:
    """convert Python's None sentinel to Nothing."""
    return Nothing if value is None else Some(value)


class _Option[T]:
    __slots__ = ()

    def __bool__(self) -> bool:
        return False

    def __iter__(self) -> Iterator[T]:
        return iter(())

    def iter(self) -> Iterator[T]:
        """a fresh iterator over zero or one values."""
        return iter(self)

    def is_some(self) -> bool:
        return False

    def is_none(self) -> bool:
        return True

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

    def unzip[A, B](
        self: _Option[tuple[A, B]],
    ) -> tuple[Option[A], Option[B]]:
        return Nothing, Nothing

    def flatten[U](self: _Option[Option[U]]) -> Option[U]:
        return Nothing


@final
@dataclass(frozen=True, slots=True, repr=False)
class Some(_Option[T]):
    """a present value, including None and other falsey values."""

    value: T

    def __init__(self, value: T) -> None:
        _set_value(self, value)

    def __repr__(self) -> str:
        return f"Some({self.value!r})"

    def __bool__(self) -> bool:
        return True

    def __iter__(self) -> Iterator[T]:
        return iter((self.value,))

    def is_some(self) -> bool:
        return True

    def is_none(self) -> bool:
        return False

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
        return Nothing if other else self

    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        return Some((self.value, other.unwrap())) if other else Nothing

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


@final
@dataclass(frozen=True, slots=True, repr=False)
class _Nothing(_Option[Never]):
    def __repr__(self) -> str:
        return "Nothing"


# a closed union preserves the payload type when matching either variant.
type Option[T] = Some[T] | _Nothing

Nothing = _Nothing()
