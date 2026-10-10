# API reference

a field guide to the duck: each operation and exactly what it promises.

import the public vocabulary from `kamo`:

```python
from kamo import Err, Iter, Nothing, NothingType, Ok, Option, Peekable
from kamo import Result, Some, from_optional
```

`T`, `E`, `U`, and `F` below describe payload types. return types describe a
union-typed receiver; a known variant often has a more precise return type.

`kamo.__version__` is the installed distribution's version string, loaded and
cached on first access. ordinary API imports avoid loading distribution
metadata.

## Option

`Option[T] = Some[T] | NothingType`. `Some(value)` represents presence;
`Nothing` is the shared absence value. `Some(None)` is present.

| operation | behavior |
| --- | --- |
| `from_optional(value)` | None becomes Nothing; another value becomes Some |
| `is_some`, `is_none` | boolean attributes describing the variant |
| `is_some_and(predicate)` | test a present payload; False on absence |
| `is_none_or(predicate)` | test a present payload; True on absence |
| `unwrap()` | return the payload; ValueError on absence |
| `expect(message)` | unwrap with the given absence error message |
| `unwrap_or(default)` | return the payload or the supplied default |
| `unwrap_or_else(factory)` | call the zero-argument factory only on absence |
| `to_optional()` | return the payload or None; loses Some(None)/Nothing distinction |
| `map(function)` | transform presence into `Option[U]` |
| `map_or(default, function)` | return the mapped value or default without a wrapper |
| `map_or_else(factory, function)` | mapped value or a lazily computed default |
| `inspect(function)` | visit a present payload and return the same Option |
| `and_(other)` | other on presence, Nothing on absence |
| `and_then(function)` | call the Option-returning function only on presence |
| `or_(other)` | retain presence; return other on absence |
| `or_else(factory)` | retain presence; call the Option factory on absence |
| `filter(predicate)` | retain accepted presence; otherwise Nothing |
| `xor(other)` | retain exactly one present input; otherwise Nothing |
| `zip(other)` | two present payloads become `Some((left, right))` |
| `zip_with(other, function)` | combine present payloads without an intermediate pair |
| `unzip()` | split an optional pair into two Options |
| `flatten()` | remove one Option layer |
| `ok_or(error)` | presence becomes Ok; absence becomes Err(error) |
| `ok_or_else(factory)` | construct the error only on absence |
| `transpose()` | `Option[Result[T, E]]` becomes `Result[Option[T], E]` |
| `iter()`, `iter(option)` | a fresh iterator yielding zero or one raw payload |

`Some[T].value` exposes the payload. `NothingType` names the absence class for
annotations and `case NothingType()` patterns. neither Option nor Result is a
runtime base class; use the variants in `isinstance` checks.

`unwrap_or`, `map_or`, `or_`, and their lazy forms may widen the output type
when a fallback has a different type. `Some`'s pass-through combinators keep
its wrapper. Some(None) and other falsey payloads remain present.

## Result

`Result[T, E] = Ok[T] | Err[E]`. `Ok(value)` represents success; `Err(error)`
represents an expected failure. each error can be any payload type.

| operation | behavior |
| --- | --- |
| `is_ok`, `is_err` | boolean attributes describing the variant |
| `is_ok_and(predicate)` | test success; False on Err |
| `is_err_and(predicate)` | test an error; False on Ok |
| `ok()` | success becomes Some; error becomes Nothing |
| `err()` | error becomes Some; success becomes Nothing |
| `unwrap()` | return success; ValueError including the error repr on Err |
| `expect(message)` | unwrap with the given message and unexpected error repr |
| `unwrap_err()` | return the error; ValueError including the value repr on Ok |
| `expect_err(message)` | unwrap the error with the given message and value repr |
| `unwrap_or(default)` | success or the supplied default |
| `unwrap_or_else(function)` | call `function(error)` only on Err |
| `map(function)` | transform success into `Result[U, E]` |
| `map_err(function)` | transform the error into `Result[T, F]` |
| `map_or(default, function)` | mapped success or default without a wrapper |
| `map_or_else(fallback, function)` | mapped success or `fallback(error)` |
| `inspect(function)` | visit success and return the same Result |
| `inspect_err(function)` | visit the error and return the same Result |
| `and_(other)` | other on Ok; retain the existing Err |
| `and_then(function)` | call the Result-returning function only on success |
| `or_(other)` | retain Ok; return other on Err |
| `or_else(function)` | retain Ok; call `function(error)` on Err |
| `flatten()` | remove one nested Result layer, retaining an outer Err |
| `transpose()` | `Result[Option[T], E]` becomes `Option[Result[T, E]]` |
| `iter()`, `iter(result)` | a fresh iterator yielding success once or nothing on Err |

`Ok[T].value` exposes success; `Err[E].error` exposes the error. an inactive
callback is skipped, and a pass-through Result keeps its wrapper. callbacks
that raise propagate their exceptions.

when sequencing, error types may widen; recovery may widen the success type.
for example, sequencing `Result[int, str]` with a function returning
`Result[float, bytes]` produces `Result[float, str | bytes]`. recovery with
that function produces `Result[int | float, bytes]`.

## Python value protocols

Some, Ok, and Err have one frozen payload slot and no instance dictionary.
Nothing has no payload. payload mutability is unchanged. equality compares
variants and their payloads; hashing requires a hashable payload. copy,
deepcopy, dataclass replacement, and pickle are supported. shallow copies
share the payload; deepcopy preserves cycles and shared references.

truth checks inspect the variant, regardless of the payload's truth. Some and
Ok are true; Nothing and Err are false. use `bool(value)`, `hash(value)`, and
`iter(value)` for these protocols. Some and Ok use Python's default object
truth rather than defining their own `__bool__` method.

explicit constructor aliases such as `Some[int]`, `Ok[int]`, and `Err[str]`
are cached native GenericAlias values. `typing.get_origin` and
`typing.get_args` expose their origin and parameters. frozen wrappers do not
store `__orig_class__`. aliases differ from private `typing` aliases in their
concrete type and equality.

## Iter adapters

`Iter[T](iterable)` captures one iterator. aliases and derived pipelines share
its position; no adapter replays the input. constructing an adapter requests
no items and does not run its transformation callback.

| operation | output and behavior |
| --- | --- |
| `map(function)` | `Iter[U]`; apply the transformation lazily |
| `filter(predicate)` | `Iter[T]`; yield accepted inputs |
| `filter_map(function)` | `Iter[U]`; yield payloads of present callback outputs |
| `map_while(function)` | `Iter[U]`; yield present outputs until the first Nothing |
| `flat_map(function)` | `Iter[U]`; concatenate callback-produced iterables |
| `flatten()` | concatenate nested iterables |
| `take(count)` | yield at most count inputs |
| `skip(count)` | skip count inputs, then yield the remainder |
| `take_while(predicate)` | yield accepted prefix; consume the first rejected input |
| `skip_while(predicate)` | skip accepted prefix; yield the first rejection and remainder |
| `scan(initial, function)` | callback receives state/input and returns `(state, Option[output])` |
| `peekable()` | a Peekable over the remaining cursor |
| `chain(other)` | yield this cursor, then other; item types may widen |
| `zip(other)` | pairs until the shorter input ends |
| `enumerate(start=0)` | `(index, value)` pairs |
| `inspect(function)` | visit each yielded input without changing its value |

map_while and scan consume the input that produces Nothing, leave later source
items unread, and remain exhausted permanently. filter_map skips Nothing and
continues. every Some(None) yields a raw None.

take and skip accept nonnegative indices according to `itertools.islice`.
zip follows Python's zip: it may consume an extra left input before discovering
that the right input is exhausted. scan does not yield its initial state.

## Iter consumers

| operation | output and behavior |
| --- | --- |
| `next()` | `Option[T]`; consume one item or return Nothing |
| `collect()` | a list of all remaining raw items |
| `partition(predicate)` | `(matching, rejected)` lists, ordered within each group |
| `count()` | number of remaining items |
| `last()` | last remaining item as an Option; Nothing on empty input |
| `nth(index)` | consume through the zero-based remaining index; Option output |
| `fold(initial, function)` | accumulate all inputs, starting with initial |
| `reduce(function)` | accumulate from the first input; Option output |
| `find(predicate)` | consume through the first match; Option output |
| `position(predicate)` | consume through a match; its remaining zero-based index |
| `find_map(function)` | first present callback output, retaining its wrapper |
| `any(predicate)` | stop at the first true output; False on empty input |
| `all(predicate)` | stop at the first false output; True on empty input |
| `for_each(function)` | visit every remaining item; return None |
| `collect_option()` | collect present payloads; stop and return Nothing on absence |
| `collect_result()` | collect successful payloads; stop and retain the first Err |
| `try_fold(initial, function)` | accumulate success; stop and retain a callback Err |
| `try_for_each(function)` | visit using Result[None, E] callbacks; stop on Err |

partition calls its predicate once per item and returns distinct empty lists
on empty input. its boolean predicate retains the item type in both outputs.
reduce returns Nothing on empty input. successful empty fallible collection
returns Some([]) or Ok([]); empty try_fold returns Ok(initial), and successful
try_for_each returns Ok(None).

short-circuiting consumers leave later items unread. count, last, and position
use bounded auxiliary storage; collect and partition retain their outputs.
callbacks and source errors propagate. Python generator callbacks that raise
StopIteration become RuntimeError; native adapters can interpret it as
exhaustion. the caller owns resource cleanup.

Iter is an iterable: `iter(values)` returns its underlying iterator, and
`next(iter(values))` returns a raw item. `list`, `tuple`, `sum`, and other
Python iterable consumers work directly. ordinary traversal creates no Option
per input; `.next()` creates a Some when it succeeds.

## Peekable

`Peekable[T](iterable)` or `Iter(...).peekable()` adds one buffered item. it is
also a Python iterator: `iter(values) is values`, and `next(values)` retrieves
a raw item. its `.next()` returns an Option, as on Iter.

| operation | behavior |
| --- | --- |
| `peek()` | fetch once and retain the next Some, including Some(None) |
| `next_if(predicate)` | consume only when the buffered payload is accepted |
| `next_if_eq(expected)` | consume only when the buffered payload equals expected |
| `peekable()` | return this existing Peekable |

repeated peeks reuse the same Some; consuming a buffered item through `.next()`
or a successful conditional also reuses it. rejection and conditional callback
exceptions retain the item. exhaustion is cached permanently. inherited
adapters, consumers, and Python iteration use the buffer; an upstream alias
bypasses it. length hints include a buffered item and report zero after cached
exhaustion.

## Rust correspondence

names and callback order follow Rust's [Option], [Result], and [Iterator]
vocabulary. Python keyword conflicts use `and_` and `or_`. predicates such as
`is_some` are boolean attributes, and iterator `collect()` returns a list.
Python references replace Rust borrowing; wrappers keep payload mutability.
mutation, unchecked access, and type-directed Default operations are absent.
Result callbacks represent early failure; this API does not add ControlFlow.

Rust's map_while leaves behavior after the first None unspecified. kamo's
map_while guarantees permanent exhaustion. wrapper iteration is a fresh
zero-or-one iterator; Iter pipelines are one-shot and share their cursor.

[Option]: https://doc.rust-lang.org/std/option/enum.Option.html
[Result]: https://doc.rust-lang.org/std/result/enum.Result.html
[Iterator]: https://doc.rust-lang.org/std/iter/trait.Iterator.html
