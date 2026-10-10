# kamo

Rust-like Option, Result, and iterator idioms for Python 3.14+.
pure Python, precise types, and no runtime dependencies.

- `Option[T]`: a present `Some(value)` or an absent `Nothing`.
- `Result[T, E]`: a successful `Ok(value)` or an expected `Err(error)`.
- `Iter[T]`: lazy, one-shot pipelines over Python's iterator machinery.
- `Peekable[T]`: the same vocabulary with one item of shared lookahead.

install from the repository with uv:

```sh
uv add 'kamo @ git+https://github.com/the-moonwitch/kamo.git'
```

```python
from kamo import Err, Iter, Nothing, Ok, Option, Result, Some


def half_even(value: int) -> Option[int]:
    return Some(value // 2) if value % 2 == 0 else Nothing


def parse_integer(text: str) -> Result[int, str]:
    try:
        return Ok(int(text))
    except ValueError:
        return Err(f"invalid integer: {text!r}")


assert Some(8).and_then(half_even).map(str) == Some("4")
assert Some(None).is_some
assert bool(Ok(False))

numbers = Iter(["1", "bad", "3"]).map(parse_integer)
assert numbers.collect_result() == Err("invalid integer: 'bad'")
assert numbers.collect_result() == Ok([3])
```

callbacks run only on the appropriate variant. truth tests inspect presence or
success rather than the payload's truth. exceptions raised by callbacks
propagate. iterator aliases share a cursor; stopping early leaves later items
available. the caller owns input resources.

read the [usage guide](docs/guide.md), [API reference](docs/reference.md), or
[development guide](docs/development.md). the small
[configuration reader](examples/configuration.py) combines optional section
boundaries with Result errors and processes a section in one pass.

names and callback order follow Rust's [Option], [Result], and [Iterator],
with Python adaptations described in the reference. the design also draws on
[returns' Maybe] and [Expression's Option].

[Option]: https://doc.rust-lang.org/std/option/enum.Option.html
[Result]: https://doc.rust-lang.org/std/result/enum.Result.html
[Iterator]: https://doc.rust-lang.org/std/iter/trait.Iterator.html
[returns' Maybe]: https://github.com/dry-python/returns/blob/master/returns/maybe.py
[Expression's Option]: https://github.com/dbrattli/Expression/blob/main/expression/core/option.py
