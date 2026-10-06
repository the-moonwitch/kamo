# kamo

a pure Python library for Rust-like Option, Result, and iterator idioms.
Python 3.14+; no runtime dependencies. Option is available; Result and iterator
combinators are next.

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

the initial API covers predicates, unwrapping, mapping, `and_then`, boolean
combinators, `filter`, `inspect`, `zip`, `unzip`, and `flatten`.
`and_` and `or_` avoid Python keywords; `or_else` takes a lazy factory.
`unwrap` and `expect` raise `ValueError` on Nothing. fallback types can widen:
calling `.unwrap_or("missing")` on an `Option[int]` returns `int | str`.
borrowing, mutation, and Result-dependent Rust methods are deferred.

`map_or(default, function)` returns the mapped payload directly, avoiding an
intermediate Some when consuming the result. `map_or_else` also makes the
fallback lazy.

truth tests check presence, including `Some(False)` and `Some(None)`. iteration
creates a fresh zero-or-one iterator each time. `to_optional()` returns the
payload or None, so that conversion loses the distinction between Some(None)
and Nothing.

`is_some` and `is_none` are boolean attributes. their values are shared class
constants, with no call or extra instance storage. `if option.is_some:` checks
presence; `if option.is_some is True:` also narrows to `Some[T]` in all supported
type checkers, allowing direct access to `option.value`.

the design draws on [returns' Maybe][returns] and [Expression's Option][expression],
with names and callback semantics following [Rust's Option][rust].

[returns]: https://github.com/dry-python/returns/blob/master/returns/maybe.py
[expression]: https://github.com/dbrattli/Expression/blob/main/expression/core/option.py
[rust]: https://doc.rust-lang.org/std/option/enum.Option.html

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

tests cover Option behavior, callback laziness, public typing, and map/bind laws
with Hypothesis. coverage locates gaps; no threshold is enforced.
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
