# kamo

a pure Python library for Rust-like Option, Result, and iterator idioms.
Python 3.14+; no runtime dependencies. Option and Result are available;
iterator combinators are next.

```python
from kamo import Nothing, Option, Some, from_optional


def half_even(value: int) -> Option[int]:
    return Some(value // 2) if value % 2 == 0 else Nothing


assert Some(8).and_then(half_even).map(str).unwrap() == "4"
assert Some(3).and_then(half_even) is Nothing
assert Nothing.map(str) is Nothing
assert Some(None).is_some
assert from_optional(None) is Nothing
assert list(Some(0)) == [0]
assert list(Nothing) == []
```

`Option[T]` is the covariant union of `Some[T]` and the absence variant.
construct with `Some(value)`, `Nothing`, or `from_optional(value)`. Some holds
one payload slot; Nothing is shared. both are immutable values, support equality
and hashing when their payload does, and have no instance dictionary. payloads
retain their own mutability. `case Some(value)` preserves the payload type.
both variants are `@final`; put domain-specific state in the payload.

`Some[int](value=1)` also supports explicit type parameters. runtime aliases
are native `types.GenericAlias` values with a bounded cache; introspect them
with `typing.get_origin` and `typing.get_args`. their concrete type and equality
with private `typing` aliases differ from the standard generic wrapper.

the initial API covers predicates, unwrapping, mapping, `and_then`, boolean
combinators, `filter`, `inspect`, `zip`, `unzip`, and `flatten`.
`zip_with(other, function)` combines two present payloads directly; its callback
receives both values and is skipped if either option is Nothing.
`and_` and `or_` avoid Python keywords; `or_else` takes a lazy factory.
`unwrap` and `expect` raise `ValueError` on Nothing. fallback types can widen:
calling `.unwrap_or("missing")` on an `Option[int]` returns `int | str`.
borrowing, mutation, and Option-to-Result Rust methods are deferred.

`map_or(default, function)` returns the mapped payload directly, avoiding an
intermediate Some when consuming the result. `map_or_else` also makes the
fallback lazy.

truth tests check presence, including `Some(False)` and `Some(None)`. iteration
creates a fresh zero-or-one iterator each time. `to_optional()` returns the
payload or None, so that conversion loses the distinction between Some(None)
and Nothing.

use `bool(option)` and `hash(option)` for the Python protocols. Some uses
default object truth and has no `__bool__` method. Nothing's constant truth,
iteration, and length-hint hooks accept no arguments, including when accessed
on its class. its zero length hint avoids allocating unused list capacity.

`is_some` and `is_none` are boolean attributes. their values are shared class
constants, with no call or extra instance storage. `if option.is_some:` checks
presence; `if option.is_some is True:` also narrows to `Some[T]` in all supported
type checkers, allowing direct access to `option.value`.

the design draws on [returns' Maybe][returns] and [Expression's Option][expression],
with names and callback semantics following [Rust's Option][rust].

[returns]: https://github.com/dry-python/returns/blob/master/returns/maybe.py
[expression]: https://github.com/dbrattli/Expression/blob/main/expression/core/option.py
[rust]: https://doc.rust-lang.org/std/option/enum.Option.html

```python
from kamo import Err, Nothing, Ok, Result, Some


def positive(value: int) -> Result[int, str]:
    return Ok(value) if value > 0 else Err("must be positive")


assert positive(8).map(str).unwrap() == "8"
assert positive(-1).map(str) == Err("must be positive")
assert positive(-1).or_else(lambda error: Ok(len(error))).unwrap() == 16
assert Ok(None).ok() == Some(None)
assert Err("missing").ok() is Nothing
assert Ok(Some(2)).transpose() == Some(Ok(2))
```

`Result[T, E]` is the covariant union of `Ok[T]` and `Err[E]`. construct with
`Ok(value)` or `Err(error)`, including keyword arguments and explicit type
parameters such as `Ok[int](value=1)` and `Err[str](error="missing")`. each
variant has one frozen payload slot and no instance dictionary. both support
value equality, hashing for hashable payloads, copy/deepcopy, and pickle.
both variants are `@final`; additional domain state belongs in the payload.
`case Ok(value)` and `case Err(error)` preserve their respective payload types.
error payloads can be any type; callback exceptions propagate unchanged.

the API follows [Rust's Result][rust-result]: predicates, `ok()` / `err()`
conversion to Option, `map`, `map_err`, `map_or`, `map_or_else`, `inspect`,
`inspect_err`, `and_`, `and_then`, `or_`, `or_else`, unwrapping, `flatten`,
and `transpose`. inactive callbacks are skipped, and pass-through methods reuse
the existing wrapper. `map_or` and `map_or_else` consume a mapped value without
allocating an intermediate Ok.

`unwrap_or_else`, `map_or_else`, and `or_else` pass the error payload to their
fallback callback. `unwrap` / `expect` on Err and `unwrap_err` / `expect_err`
on Ok raise `ValueError` with the unexpected payload's representation.
Python's value and error types can widen: chaining a `Result[int, str]` with
a function returning `Result[float, bytes]` gives `Result[float, str | bytes]`;
recovering with it gives `Result[int | float, bytes]`.

`is_ok` and `is_err` are shared boolean attributes. `if result.is_ok is True:`
narrows to Ok in all supported type checkers; the corresponding Err check
narrows to Err. truth tests distinguish success from error regardless of the
payload's truth. iteration yields the successful value once or nothing on Err,
with a fresh iterator each time. borrowing, mutation, unchecked access, and
Rust's type-directed Default methods have no direct equivalent in this API.

`NothingType` names the existing absence class for annotations and pattern
matching; `Nothing` remains the shared absence value. Result's `transpose()`
turns `Ok(Some(value))` into `Some(Ok(value))`, `Ok(Nothing)` into Nothing,
and `Err(error)` into `Some(Err(error))`.

[rust-result]: https://doc.rust-lang.org/std/result/enum.Result.html

```sh
mise trust
mise install
mise run setup
mise run check
mise run test
```

mise pins uv; uv manages Python and the locked development dependencies.
development, runtime code, and public types target Python 3.14.

| task | purpose |
| --- | --- |
| `mise run format` | Ruff lint fixes and formatting at 79 columns |
| `mise run check` | Ruff, BasedPyright, mypy, and upstream Pyright |
| `mise run test` | pytest with branch coverage |
| `mise run fuzz` | pytest with a 5000-example Hypothesis profile |
| `mise run bench -- '<expression>'` | pyperf timing for an expression |
| `mise run profile -- path/to/workload.py` | Pyinstrument sampling profile |
| `mise run build` | wheel and source distribution |
| `mise run outdated` | available dependency updates |

tests cover Option and Result behavior, callback laziness, public typing, and
map/bind laws with Hypothesis. coverage locates gaps; no threshold is enforced.
`tests/conftest.py` registers reproducible CI and larger fuzz profiles.

benchmarks and profiles use the tools directly. for example:

```sh
mise run bench -- --fast -s 'from kamo import Some; x = Some(42)' 'x.map(str)'
mise run profile -- -m pytest
```

`pyrightconfig.json` is shared by BasedPyright, Pyright, and Pylance; mypy uses
`pyproject.toml`. Pylance runs in the editor; CI checks upstream Pyright.
`AGENTS.md`, `.zed/`, and `.vscode/` stay local and ignored.

CI checks lint, types, and builds, and runs tests on Python 3.14 across linux,
macOS, and windows. the default `dev` dependency group includes the test tools;
compatibility jobs install only the `test` group.
