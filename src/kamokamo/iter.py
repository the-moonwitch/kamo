"""lazy one-shot pipelines over Python's iterator machinery."""

from collections.abc import Callable, Iterable, Iterator
from functools import reduce
from itertools import chain, dropwhile, islice, takewhile
from operator import length_hint
from typing import Generic, Never, TypeVar, final, overload

from kamokamo.option import Nothing, NothingType, Option, Some
from kamokamo.result import Err, Ok, Result

__all__ = ["Iter", "Peekable"]

T = TypeVar("T", covariant=True)
U = TypeVar("U")
# a successful callback needs no inferred error type.
E = TypeVar("E", default=Never)


# explicit covariance preserves item relationships in all supported checkers.
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
        return Iter(map(function, self))

    def filter(self, predicate: Callable[[T], bool]) -> Iter[T]:
        return Iter(filter(predicate, self))

    @overload
    def filter_map(
        self, function: Callable[[T], NothingType]
    ) -> Iter[Never]: ...

    @overload
    def filter_map[U](self, function: Callable[[T], Option[U]]) -> Iter[U]: ...

    def filter_map[U](self, function: Callable[[T], Option[U]]) -> Iter[U]:
        return Iter(_filter_map(self, function))

    @overload
    def map_while(
        self, function: Callable[[T], NothingType]
    ) -> Iter[Never]: ...

    @overload
    def map_while[U](self, function: Callable[[T], Option[U]]) -> Iter[U]: ...

    def map_while[U](self, function: Callable[[T], Option[U]]) -> Iter[U]:
        """yield present outputs until Nothing; leave later inputs unread."""
        return Iter(_map_while(self, function))

    def flat_map[U](self, function: Callable[[T], Iterable[U]]) -> Iter[U]:
        return Iter(chain.from_iterable(map(function, self)))

    def flatten[U](self: Iter[Iterable[U]]) -> Iter[U]:
        return Iter(chain.from_iterable(self))

    def take(self, count: int) -> Iter[T]:
        return Iter(islice(self, count))

    def skip(self, count: int) -> Iter[T]:
        return Iter(islice(self, count, None))

    def take_while(self, predicate: Callable[[T], bool]) -> Iter[T]:
        """yield a prefix, consuming the first item failing the predicate."""
        return Iter(takewhile(predicate, self))

    def skip_while(self, predicate: Callable[[T], bool]) -> Iter[T]:
        return Iter(dropwhile(predicate, self))

    @overload
    def scan[S](
        self, initial: S, function: Callable[[S, T], tuple[S, NothingType]]
    ) -> Iter[Never]: ...

    @overload
    def scan[S, U](
        self, initial: S, function: Callable[[S, T], tuple[S, Option[U]]]
    ) -> Iter[U]: ...

    def scan[S, U](
        self, initial: S, function: Callable[[S, T], tuple[S, Option[U]]]
    ) -> Iter[U]:
        """yield stateful outputs until Nothing; leave later inputs unread."""
        return Iter(_scan(self, initial, function))

    def peekable(self) -> Peekable[T]:
        """give the remaining cursor a single item of lookahead."""
        return Peekable(self)

    def chain[U](self, other: Iterable[U]) -> Iter[T | U]:
        return Iter(chain(self, other))

    def zip[U](self, other: Iterable[U]) -> Iter[tuple[T, U]]:
        return Iter(zip(self, other, strict=False))

    def enumerate(self, start: int = 0) -> Iter[tuple[int, T]]:
        return Iter(enumerate(self, start))

    def inspect(self, function: Callable[[T], object]) -> Iter[T]:
        return Iter(_inspect(self, function))

    def collect(self) -> list[T]:
        """consume the remaining items into a list."""
        return list(self)

    def partition(
        self, predicate: Callable[[T], bool]
    ) -> tuple[list[T], list[T]]:
        """consume into matching and rejected lists, preserving their order."""
        matching: list[T] = []
        rejected: list[T] = []
        for value in self:
            (matching if predicate(value) else rejected).append(value)
        return matching, rejected

    def count(self) -> int:
        """consume and count the remaining items."""
        total = 0
        for _ in self:
            total += 1
        return total

    def last(self) -> Option[T]:
        """consume the remaining items and return the last, if present."""
        cursor = iter(self)
        try:
            _last = next(cursor)
        except StopIteration:
            return Nothing
        for _last in cursor:
            pass
        return Some(_last)

    def nth(self, index: int) -> Option[T]:
        """consume and return the zero-based nth remaining item."""
        remaining = islice(self, index, None)
        try:
            value = next(remaining)
        except StopIteration:
            return Nothing
        return Some(value)

    def fold[U](self, initial: U, function: Callable[[U, T], U]) -> U:
        return reduce(function, self, initial)

    def reduce(self, function: Callable[[T, T], T]) -> Option[T]:
        try:
            initial = next(iter(self))
        except StopIteration:
            return Nothing
        return Some(reduce(function, self, initial))

    def find(self, predicate: Callable[[T], bool]) -> Option[T]:
        for value in self:
            if predicate(value):
                return Some(value)
        return Nothing

    def position(self, predicate: Callable[[T], bool]) -> Option[int]:
        """consume through a match; return its zero-based remaining index."""
        index = 0
        for value in self:
            if predicate(value):
                return Some(index)
            index += 1  # noqa: SIM113 - measured faster with the JIT.
        return Nothing

    def find_map[O: Option[object]](
        self, function: Callable[[T], O]
    ) -> O | NothingType:
        for value in self:
            result = function(value)
            if result.is_some:
                return result
        return Nothing

    def any(self, predicate: Callable[[T], bool]) -> bool:
        return any(map(predicate, self))

    def all(self, predicate: Callable[[T], bool]) -> bool:
        return all(map(predicate, self))

    def for_each(self, function: Callable[[T], object]) -> None:
        for value in self:
            function(value)

    @overload
    def collect_option[U](self: Iter[Some[U]]) -> Some[list[U]]: ...

    @overload
    def collect_option(self: Iter[NothingType]) -> Option[list[Never]]: ...

    @overload
    def collect_option[U](self: Iter[Option[U]]) -> Option[list[U]]: ...

    def collect_option[U](self: Iter[Option[U]]) -> Option[list[U]]:
        values: list[U] = []
        for result in self:
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
        for result in self:
            if result.is_ok is True:
                values.append(result.value)
            else:
                return result
        return Ok(values)

    def try_fold(
        self, initial: U, function: Callable[[U, T], Result[U, E]]
    ) -> Result[U, E]:
        """fold until the callback returns Err; leave later items unread."""
        for value in self:
            result = function(initial, value)
            if result.is_ok is True:
                initial = result.value
            else:
                return result
        return Ok(initial)

    def try_for_each[R: Result[None, object]](
        self, function: Callable[[T], R]
    ) -> R | Ok[None]:
        for value in self:
            result = function(value)
            if result.is_err is True:
                return result
        return Ok(None)


def _filter_map[T, U](
    source: Iterable[T], function: Callable[[T], Option[U]]
) -> Iterator[U]:
    for value in source:
        result = function(value)
        if result.is_some is True:
            yield result.value


def _map_while[T, U](
    source: Iterable[T], function: Callable[[T], Option[U]]
) -> Iterator[U]:
    for value in source:
        result = function(value)
        if result.is_some is True:
            yield result.value
        else:
            return


def _inspect[T](
    source: Iterable[T], function: Callable[[T], object]
) -> Iterator[T]:
    for value in source:
        function(value)
        yield value


def _scan[T, S, U](
    source: Iterable[T],
    state: S,
    function: Callable[[S, T], tuple[S, Option[U]]],
) -> Iterator[U]:
    for value in source:
        state, result = function(state, value)
        if result.is_some is True:
            yield result.value
        else:
            return


@final
class Peekable(Iter[T]):
    """a Python iterator with cached lookahead and conditional consumption."""

    __slots__ = ("_buffer",)

    def __init__(self, iterable: Iterable[T]) -> None:
        # unbound generic access loses T in Pyright; this signature retains it.
        Iter.__init__(self, iterable)  # pyright: ignore[reportUnknownMemberType]
        # None means unfilled; Nothing means exhausted; Some(None) is an item.
        self._buffer: Option[T] | None = None

    def __iter__(self) -> Peekable[T]:
        return self

    def __next__(self) -> T:
        buffered = self._buffer
        if buffered is None:
            try:
                return next(self._iterator)
            except StopIteration:
                self._buffer = Nothing
                raise
        if buffered.is_some is True:
            self._buffer = None
            return buffered.value
        raise StopIteration

    def __length_hint__(self) -> int:
        buffered = self._buffer
        if buffered is None:
            return length_hint(self._iterator)
        if buffered.is_some:
            return length_hint(self._iterator) + 1
        return 0

    def peek(self) -> Option[T]:
        """observe the next item, pulling it from the source only once."""
        buffered = self._buffer
        if buffered is None:
            try:
                value = next(self._iterator)
            except StopIteration:
                buffered = Nothing
            else:
                buffered = Some(value)
            self._buffer = buffered
        return buffered

    def next(self) -> Option[T]:
        buffered = self._buffer
        if buffered is None:
            try:
                value = next(self._iterator)
            except StopIteration:
                self._buffer = Nothing
                return Nothing
            return Some(value)
        if buffered.is_some:
            self._buffer = None
        return buffered

    def next_if(self, predicate: Callable[[T], bool]) -> Option[T]:
        """consume only on acceptance; callback errors retain the item."""
        buffered = self.peek()
        if buffered.is_some is True and predicate(buffered.value):
            self._buffer = None
            return buffered
        return Nothing

    def next_if_eq(self, expected: object) -> Option[T]:
        buffered = self.peek()
        if buffered.is_some is True and buffered.value == expected:
            self._buffer = None
            return buffered
        return Nothing

    def peekable(self) -> Peekable[T]:
        return self
