"""immutable success and error values, with Rust-style combinators."""

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

from kamo.option import Nothing, NothingType, Option, Some

__all__ = ["Err", "Ok", "Result"]

T = TypeVar("T", covariant=True)
E = TypeVar("E", covariant=True)


def _class_getitem(cls: type[object], parameters: object) -> GenericAlias:
    try:
        return _cached_alias(cls, parameters)
    except TypeError:
        # valid type arguments can have an unhashable metaclass.
        return _alias(cls, parameters)


class _ResultBase:
    __slots__ = ()

    __class_getitem__ = classmethod(_class_getitem)


# explicit covariance keeps variant methods precise in all supported checkers.
@final
@dataclass(frozen=True, slots=True, repr=False)
class Ok(_ResultBase, Generic[T]):  # noqa: UP046
    """a successful value, including None and other falsey values."""

    value: T
    is_ok: ClassVar[Literal[True]] = True
    is_err: ClassVar[Literal[False]] = False

    def __init__(self, value: T) -> None:
        _set_ok(self, value)

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"

    def __copy__(self) -> Ok[T]:
        return Ok(self.value)

    def __deepcopy__(self, memo: dict[int, object]) -> Ok[T]:
        result = object.__new__(type(self))
        memo[id(self)] = result
        _set_ok(result, deepcopy(self.value, memo))
        return result

    def __getstate__(self) -> tuple[T]:
        return (self.value,)

    def __setstate__(self, state: Iterable[object]) -> None:
        for value in state:
            _set_ok(self, value)
            break

    def __iter__(self) -> Iterator[T]:
        return iter((self.value,))

    iter = __iter__

    def is_ok_and(self, predicate: Callable[[T], bool]) -> bool:
        return predicate(self.value)

    def is_err_and(self, predicate: Callable[[Never], bool]) -> bool:
        return False

    def ok(self) -> Some[T]:
        return Some(self.value)

    def err(self) -> NothingType:
        return Nothing

    def unwrap(self) -> T:
        return self.value

    def expect(self, message: str) -> T:
        return self.value

    def unwrap_err(self) -> Never:
        raise ValueError(f"called unwrap_err on Ok: {self.value!r}")

    def expect_err(self, message: str) -> Never:
        raise ValueError(f"{message}: {self.value!r}")

    def unwrap_or(self, default: object) -> T:
        return self.value

    def unwrap_or_else[U](self, default: Callable[[Never], U]) -> T:
        return self.value

    def map[U](self, function: Callable[[T], U]) -> Ok[U]:
        return Ok(function(self.value))

    def map_err[F](self, function: Callable[[Never], F]) -> Self:
        return self

    def map_or[U](self, default: object, function: Callable[[T], U]) -> U:
        return function(self.value)

    def map_or_else[U, V](
        self, default: Callable[[Never], U], function: Callable[[T], V]
    ) -> V:
        return function(self.value)

    def inspect(self, function: Callable[[T], object]) -> Self:
        function(self.value)
        return self

    def inspect_err(self, function: Callable[[Never], object]) -> Self:
        return self

    def and_[R: Result[object, object]](self, other: R) -> R:
        return other

    def and_then[R: Result[object, object]](
        self, function: Callable[[T], R]
    ) -> R:
        return function(self.value)

    def or_[U, F](self, other: Result[U, F]) -> Self:
        return self

    def or_else[U, F](self, default: Callable[[Never], Result[U, F]]) -> Self:
        return self

    @overload
    def flatten[U](self: Ok[Ok[U]]) -> Ok[U]: ...

    @overload
    def flatten[F](self: Ok[Err[F]]) -> Err[F]: ...

    @overload
    def flatten[U, F](self: Ok[Result[U, F]]) -> Result[U, F]: ...

    def flatten[U, F](self: Ok[Result[U, F]]) -> Result[U, F]:
        return self.value

    @overload
    def transpose[U](self: Ok[Some[U]]) -> Some[Ok[U]]: ...

    @overload
    def transpose(self: Ok[NothingType]) -> NothingType: ...

    @overload
    def transpose[U](self: Ok[Option[U]]) -> Option[Ok[U]]: ...

    def transpose[U](self: Ok[Option[U]]) -> Option[Ok[U]]:
        return (
            Some(Ok(self.value.value))
            if self.value.is_some is True
            else Nothing
        )


@final
@dataclass(frozen=True, slots=True, repr=False)
class Err(_ResultBase, Generic[E]):  # noqa: UP046
    """an error payload, without requiring an exception."""

    error: E
    is_ok: ClassVar[Literal[False]] = False
    is_err: ClassVar[Literal[True]] = True

    def __init__(self, error: E) -> None:
        _set_err(self, error)

    def __repr__(self) -> str:
        return f"Err({self.error!r})"

    def __copy__(self) -> Err[E]:
        return Err(self.error)

    def __deepcopy__(self, memo: dict[int, object]) -> Err[E]:
        result = object.__new__(type(self))
        memo[id(self)] = result
        _set_err(result, deepcopy(self.error, memo))
        return result

    def __getstate__(self) -> tuple[E]:
        return (self.error,)

    def __setstate__(self, state: Iterable[object]) -> None:
        for error in state:
            _set_err(self, error)
            break

    # native constant hooks avoid Python frames and speculative list capacity.
    __bool__ = False.__bool__
    __iter__ = ().__iter__
    iter = __iter__
    __length_hint__ = ().__len__

    def is_ok_and(self, predicate: Callable[[Never], bool]) -> bool:
        return False

    def is_err_and(self, predicate: Callable[[E], bool]) -> bool:
        return predicate(self.error)

    def ok(self) -> NothingType:
        return Nothing

    def err(self) -> Some[E]:
        return Some(self.error)

    def unwrap(self) -> Never:
        raise ValueError(f"called unwrap on Err: {self.error!r}")

    def expect(self, message: str) -> Never:
        raise ValueError(f"{message}: {self.error!r}")

    def unwrap_err(self) -> E:
        return self.error

    def expect_err(self, message: str) -> E:
        return self.error

    def unwrap_or[U](self, default: U) -> U:
        return default

    def unwrap_or_else[U](self, default: Callable[[E], U]) -> U:
        return default(self.error)

    def map[U](self, function: Callable[[Never], U]) -> Self:
        return self

    def map_err[F](self, function: Callable[[E], F]) -> Err[F]:
        return Err(function(self.error))

    def map_or[U, V](self, default: U, function: Callable[[Never], V]) -> U:
        return default

    def map_or_else[U, V](
        self, default: Callable[[E], U], function: Callable[[Never], V]
    ) -> U:
        return default(self.error)

    def inspect(self, function: Callable[[Never], object]) -> Self:
        return self

    def inspect_err(self, function: Callable[[E], object]) -> Self:
        function(self.error)
        return self

    def and_[U, F](self, other: Result[U, F]) -> Self:
        return self

    def and_then[U, F](
        self, function: Callable[[Never], Result[U, F]]
    ) -> Self:
        return self

    def or_[R: Result[object, object]](self, other: R) -> R:
        return other

    def or_else[R: Result[object, object]](
        self, default: Callable[[E], R]
    ) -> R:
        return default(self.error)

    def flatten(self) -> Self:
        return self

    def transpose(self) -> Some[Self]:
        return Some(self)


_set_ok: Callable[[object, object], None] = cast(
    MemberDescriptorType, Ok.__dict__["value"]
).__set__
_set_err: Callable[[object, object], None] = cast(
    MemberDescriptorType, Err.__dict__["error"]
).__set__


class _ResultAlias(GenericAlias):
    __slots__ = ()

    def __getitem__(self, parameters: object) -> GenericAlias:
        specialized = super().__getitem__(parameters)
        return type(self)(
            cast("type[object]", self.__origin__), specialized.__args__
        )


class _OkAlias(_ResultAlias):
    __slots__ = ()
    __call__ = Ok


class _ErrAlias(_ResultAlias):
    __slots__ = ()
    __call__ = Err


_generic_getitem = cast(
    ClassMethodDescriptorType, Generic.__dict__["__class_getitem__"]
)


def _alias(cls: type[object], parameters: object) -> GenericAlias:
    getitem = cast(
        "Callable[[object], object]", _generic_getitem.__get__(None, cls)
    )
    alias_type = (
        _OkAlias if cls is Ok else _ErrAlias if cls is Err else GenericAlias
    )
    return alias_type(cls, get_args(getitem(parameters)))


_cached_alias = cast(
    "Callable[[type[object], object], GenericAlias]",
    lru_cache(maxsize=128)(_alias),
)


type Result[T, E] = Ok[T] | Err[E]
