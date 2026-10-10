"""lazy one-shot pipelines over Python's iterator machinery."""

from collections.abc import Callable, Iterable, Iterator
from functools import reduce
from itertools import chain, islice
from operator import length_hint
from typing import Generic, Never, TypeVar, final, overload

from kamo.option import Nothing, NothingType, Option, Some
from kamo.result import Err, Ok, Result

__all__ = ["Iter"]

T = TypeVar("T", covariant=True)
U = TypeVar("U")
# a successful callback needs no inferred error type.
E = TypeVar("E", default=Never)


# explicit covariance preserves item relationships in all supported checkers.
@final
class Iter(Generic[T]):  # noqa: UP046
    """a fluent iterable sharing one cursor with its derived pipelines."""

    __slots__ = ("_iterator",)

    def __init__(self, iterable: Iterable[T]) -> None:
        self._iterator = iter(iterable)

    def __iter__(self) -> Iterator[T]:
        return self._iterator

    def __length_hint__(self) -> int:
        return length_hint(self._iterator)

    def next(self) -> Option[T]:
        """consume one item, distinguishing Some(None) from exhaustion."""
        try:
            value = next(self._iterator)
        except StopIteration:
            return Nothing
        return Some(value)

    def map[U](self, function: Callable[[T], U]) -> Iter[U]:
        return Iter(map(function, self._iterator))

    def filter(self, predicate: Callable[[T], bool]) -> Iter[T]:
        return Iter(filter(predicate, self._iterator))

    @overload
    def filter_map(
        self, function: Callable[[T], NothingType]
    ) -> Iter[Never]: ...

    @overload
    def filter_map[U](self, function: Callable[[T], Option[U]]) -> Iter[U]: ...

    def filter_map[U](self, function: Callable[[T], Option[U]]) -> Iter[U]:
        return Iter(_filter_map(self._iterator, function))

    def flat_map[U](self, function: Callable[[T], Iterable[U]]) -> Iter[U]:
        return Iter(chain.from_iterable(map(function, self._iterator)))

    def flatten[U](self: Iter[Iterable[U]]) -> Iter[U]:
        return Iter(chain.from_iterable(self._iterator))

    def take(self, count: int) -> Iter[T]:
        return Iter(islice(self._iterator, count))

    def skip(self, count: int) -> Iter[T]:
        return Iter(islice(self._iterator, count, None))

    def chain[U](self, other: Iterable[U]) -> Iter[T | U]:
        return Iter(chain(self._iterator, other))

    def zip[U](self, other: Iterable[U]) -> Iter[tuple[T, U]]:
        return Iter(zip(self._iterator, other, strict=False))

    def enumerate(self, start: int = 0) -> Iter[tuple[int, T]]:
        return Iter(enumerate(self._iterator, start))

    def inspect(self, function: Callable[[T], object]) -> Iter[T]:
        return Iter(_inspect(self._iterator, function))

    def collect(self) -> list[T]:
        """consume the remaining items into a list."""
        return list(self._iterator)

    def fold[U](self, initial: U, function: Callable[[U, T], U]) -> U:
        return reduce(function, self._iterator, initial)

    def reduce(self, function: Callable[[T, T], T]) -> Option[T]:
        try:
            initial = next(self._iterator)
        except StopIteration:
            return Nothing
        return Some(reduce(function, self._iterator, initial))

    def find(self, predicate: Callable[[T], bool]) -> Option[T]:
        for value in self._iterator:
            if predicate(value):
                return Some(value)
        return Nothing

    def find_map[O: Option[object]](
        self, function: Callable[[T], O]
    ) -> O | NothingType:
        for value in self._iterator:
            result = function(value)
            if result.is_some:
                return result
        return Nothing

    def any(self, predicate: Callable[[T], bool]) -> bool:
        return any(map(predicate, self._iterator))

    def all(self, predicate: Callable[[T], bool]) -> bool:
        return all(map(predicate, self._iterator))

    def for_each(self, function: Callable[[T], object]) -> None:
        for value in self._iterator:
            function(value)

    @overload
    def collect_option[U](self: Iter[Some[U]]) -> Some[list[U]]: ...

    @overload
    def collect_option(self: Iter[NothingType]) -> Option[list[Never]]: ...

    @overload
    def collect_option[U](self: Iter[Option[U]]) -> Option[list[U]]: ...

    def collect_option[U](self: Iter[Option[U]]) -> Option[list[U]]:
        values: list[U] = []
        for result in self._iterator:
            if result.is_some is True:
                values.append(result.value)
            else:
                return Nothing
        return Some(values)

    @overload
    def collect_result[U](self: Iter[Ok[U]]) -> Ok[list[U]]: ...

    @overload
    def collect_result[E](self: Iter[Err[E]]) -> Result[list[Never], E]: ...

    @overload
    def collect_result[U, E](
        self: Iter[Result[U, E]],
    ) -> Result[list[U], E]: ...

    def collect_result[U, E](self: Iter[Result[U, E]]) -> Result[list[U], E]:
        values: list[U] = []
        for result in self._iterator:
            if result.is_ok is True:
                values.append(result.value)
            else:
                return result
        return Ok(values)

    def try_fold(
        self, initial: U, function: Callable[[U, T], Result[U, E]]
    ) -> Result[U, E]:
        """fold until the callback returns Err; leave later items unread."""
        for value in self._iterator:
            result = function(initial, value)
            if result.is_ok is True:
                initial = result.value
            else:
                return result
        return Ok(initial)

    def try_for_each[R: Result[None, object]](
        self, function: Callable[[T], R]
    ) -> R | Ok[None]:
        for value in self._iterator:
            result = function(value)
            if result.is_err is True:
                return result
        return Ok(None)


def _filter_map[T, U](
    source: Iterator[T], function: Callable[[T], Option[U]]
) -> Iterator[U]:
    for value in source:
        result = function(value)
        if result.is_some is True:
            yield result.value


def _inspect[T](
    source: Iterator[T], function: Callable[[T], object]
) -> Iterator[T]:
    for value in source:
        function(value)
        yield value
