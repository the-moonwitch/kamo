# kamo

a Python library scaffold for Rust-like Option, Result, and iterator idioms.
Python 3.14+; no runtime dependencies. the public API is still to be implemented.

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

Hypothesis is ready for property tests as library operations are added. the
current test is a package version smoke test. no coverage threshold is enforced
while the library is empty. `tests/conftest.py` registers reproducible CI and
larger fuzz profiles.

benchmarks and profiles use the tools directly. for example:

```sh
mise run bench -- --fast 'sum(range(1000))'
mise run profile -- -m pytest
```

`pyrightconfig.json` is shared by BasedPyright, Pyright, and Pylance; mypy uses
`pyproject.toml`. Pylance runs in the editor; CI checks upstream Pyright.
`AGENTS.md`, `.zed/`, and `.vscode/` stay local and ignored.

CI checks lint, types, and builds, and runs tests on Python 3.14 across linux,
macOS, and windows. the default `dev` dependency
group includes the test tools; compatibility jobs install only the `test` group.
