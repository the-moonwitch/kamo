# using kamokamo

welcome to the pond. kamokamo distinguishes a missing value, an expected failure,
and an exhausted iterator. its wrappers are immutable; their payloads keep
their own mutability. Python 3.14 or newer is required.

## optional values

our maybe: a duck in the pond, or no duck at all.

`Option[T]` is `Some[T] | NothingType`. use `Some(value)` for presence and the
shared `Nothing` value for absence. presence is independent of truthiness:

```python
from kamokamo import Nothing, Option, Some, from_optional

assert Some(None).is_some
assert bool(Some(False))
assert not Nothing
assert from_optional(None) is Nothing
assert Some(None).to_optional() is None
```

`from_optional` treats Python's None as absence. `to_optional` returns None for
both Nothing and Some(None), so use the Option itself when that distinction
matters.

`map` transforms a present payload; `and_then` calls a function that already
returns an Option. callbacks are skipped on absence.

```python
from kamokamo import Nothing, Option, Some


def half_even(value: int) -> Option[int]:
    return Some(value // 2) if value % 2 == 0 else Nothing


assert Some(8).and_then(half_even).map(str) == Some("4")
assert Some(3).and_then(half_even) is Nothing
assert Nothing.map(str) is Nothing
assert Some(0).unwrap_or(99) == 0
assert Nothing.unwrap_or_else(lambda: 99) == 99
```

`unwrap` and `expect` return the payload or raise ValueError on absence. use a
fallback when absence is expected. ordinary arguments are evaluated before a
method runs; an `_else` callback delays its work until it is needed.

## expected failures

when a computation goes swimmingly, return `Ok`. an expected failure gets an
`Err` with something useful to tell the caller.

`Result[T, E]` is `Ok[T] | Err[E]`. the error can be a string, an exception,
or a structured domain value. turn exceptions into Err at the boundary that
knows which failures are expected:

```python
from kamokamo import Err, Ok, Result


def parse_port(text: str) -> Result[int, str]:
    try:
        port = int(text)
    except ValueError:
        return Err(f"invalid port: {text!r}")
    return Ok(port) if 1 <= port <= 65535 else Err("port out of range")


assert parse_port("8080").map(str) == Ok("8080")
assert parse_port("bad").map(str) == Err("invalid port: 'bad'")
assert parse_port("0").unwrap_or(8080) == 8080
assert parse_port("bad").or_else(lambda error: Ok(len(error))) == Ok(19)
```

`map_err` transforms an error. `and_then` composes successful computations;
`or_else` recovers from an error. Result's fallback callbacks receive the error
payload, while Option's fallback factories receive no arguments. exceptions
raised by callbacks propagate; they are not converted to Err automatically.

## narrowing and matching

`is_some`, `is_none`, `is_ok`, and `is_err` are boolean attributes. use
ordinary truth tests to choose a branch. an explicit identity check narrows the
variant consistently in BasedPyright, mypy, and Pyright/Pylance:

```python
from typing import assert_type

from kamokamo import Err, Nothing, NothingType, Ok, Option, Result, Some


def describe_option(value: Option[int]) -> str:
    if value.is_some is True:
        assert_type(value, Some[int])
        return str(value.value)
    assert_type(value, NothingType)
    return "missing"


def describe_result(result: Result[int, str]) -> str:
    match result:
        case Ok(value):
            assert_type(value, int)
            return str(value)
        case Err(error):
            assert_type(error, str)
            return error


assert describe_option(Some(0)) == "0"
assert describe_option(Nothing) == "missing"
assert describe_result(Err("bad")) == "bad"
```

use `case NothingType()` to match absence. `case Nothing` is a Python capture
pattern, which binds a name rather than comparing with the shared value.
`Option` and `Result` are type aliases; use their concrete variants with
`isinstance` and class patterns. the variants are marked final for type
checkers; put additional domain state in their payloads.

all payload types are covariant. mixed collections sometimes need an explicit
`list[Option[T]]` or `list[Result[T, E]]` annotation. normal constructors infer
their payload type; `Some[int](value=1)`, `Ok[int](value=1)`, and
`Err[str](error="bad")` also accept explicit type parameters.

## crossing between absence and failure

use `ok_or` or `ok_or_else` when a missing value becomes an error. use `ok()`
or `err()` when selecting one side of a Result as an Option. `transpose`
exchanges the order of the two wrappers:

```python
from kamokamo import Err, Nothing, Ok, Some

assert Some(None).ok_or("missing") == Ok(None)
assert Nothing.ok_or_else(lambda: "missing") == Err("missing")
assert Err("bad").ok() is Nothing
assert Err("bad").err() == Some("bad")
assert Some(Ok(None)).transpose() == Ok(Some(None))
assert Some(Err("bad")).transpose() == Err("bad")
assert Ok(Nothing).transpose() is Nothing
assert Nothing.transpose() == Ok(Nothing)
```

## one-shot pipelines

let values paddle through, one at a time.

`Iter(iterable)` captures one Python iterator. adapters are lazy, and every
alias shares that cursor. consume through Python iteration or use `.next()`
for an Option. Iter is an iterable; `next(iter(values))` retrieves a raw item.
Peekable, introduced below, is also a Python iterator.

```python
from kamokamo import Iter, Some

values = Iter(range(8))
prefix = values.map(lambda value: value + 1).filter(
    lambda value: value % 2 == 0
)
assert prefix.take(2).collect() == [2, 4]
assert values.next() == Some(4)
assert list(values) == [5, 6, 7]
assert values.collect() == []
```

operator order determines which inputs are read. `take(10).filter_map(parse)`
examines at most ten inputs. `filter_map(parse).take(10)` seeks ten present
outputs and may read more inputs. `filter_map` skips absent outputs;
`map_while` stops on the first absence, consumes that stopping input, and
leaves subsequent inputs unread. Some(None) always yields a real None.

`take_while` also consumes its first rejected input. `skip_while` yields its
first rejected input and stops testing later items. `scan` carries state:
its callback returns `(new_state, Option[output])`; Nothing ends the adapter
permanently. `map_while` also stays exhausted permanently.

`collect_result` and `collect_option` stop on the first failure or absence.
after that, the remaining source is available to the caller:

```python
from kamokamo import Err, Iter, Ok, Result

ports = Iter(["8080", "bad", "443"]).map(parse_port)
assert ports.collect_result() == Err("invalid port: 'bad'")
assert ports.collect_result() == Ok([443])
assert Iter[Result[int, str]]([]).collect_result() == Ok([])
```

`try_fold` stops when its accumulation callback returns Err. `try_for_each`
stops when a visit fails; a successful visit returns Ok(None). callback and
source exceptions remain exceptions. generator callbacks that raise
StopIteration become RuntimeError, while Python's map/filter and other native
adapters may interpret StopIteration as exhaustion.

## retaining a delimiter

a curious duck likes a little lookahead.

Peekable keeps one item of lookahead. repeated `peek()` calls return the same
Some, and a rejected `next_if` leaves that item available. derived adapters,
Python iteration, and inherited consumers all use the same buffer:

```python
from kamokamo import Iter, Nothing, Some

characters = Iter("12+34").peekable()
assert characters.next_if(str.isdecimal) == Some("1")
assert characters.peek() == Some("2")
assert characters.next_if(str.isdecimal) == Some("2")
assert characters.next_if(str.isdecimal) is Nothing
assert characters.peek() == Some("+")
assert characters.next_if_eq("+") == Some("+")
assert characters.collect() == ["3", "4"]
```

consume through the Peekable once lookahead is introduced; an upstream alias
bypasses its buffer. exhaustion is cached, and a conditional callback failure
retains the buffered item.

## streams and resource ownership

the caller owns input resources. consume file-backed pipelines within the
file's context manager, including pipelines that stop early. Iter does not
close a file or generator when a consumer returns.

the following example runs from a checkout or unpacked source distribution,
where the `examples` package is available.

```python
from io import StringIO

from examples.configuration import read_section
from kamokamo import Iter

with StringIO("port=8080\nbroken\n\nnext=yes\n") as source:
    lines = Iter(source)
    assert read_section(lines) == (
        {"port": "8080"},
        ["invalid entry: 'broken'"],
    )
    assert read_section(lines) == ({"next": "yes"}, [])
    assert not source.closed
assert source.closed
```

this [configuration reader](configuration.md) ends a section at a
blank line, retains malformed-entry errors, and lets the last duplicate key
win. it assembles results in one pass so intermediate Result objects can be
released promptly. keys must be nonempty; values may be empty and contain `=`.

use `partition` when both groups of original items are needed. it preserves
order and calls the predicate once per input:

```python
from kamokamo import Iter

assert Iter(range(6)).partition(lambda value: value % 2 == 0) == (
    [0, 2, 4],
    [1, 3, 5],
)
```

for a terminal mapped value, `map_or` and `map_or_else` avoid constructing an
intermediate Some or Ok. ordinary Iter traversal also avoids wrapping every
item in an Option; `.next()` creates that wrapper intentionally. lazy
composition retains a cursor, while `collect` and `partition` retain their
outputs. a direct loop can be faster when it avoids wrappers or intermediate
collections; measure the whole workload when choosing its shape.

see the [API reference](reference.md) for the complete vocabulary and
[development guide](development.md) for checks, benchmarks, and profiling.
