# developing kamo

work from a checkout with mise installed:

```sh
mise trust
mise install
mise run setup
mise run check
mise run test
```

mise pins uv. uv installs Python and the locked development dependencies.
the package and public types support Python 3.14+. the default dev group
includes the test tools; CI's compatibility jobs install only the test group.

| task | purpose |
| --- | --- |
| `mise run format` | Ruff fixes and formatting at 79 columns |
| `mise run check` | Ruff, BasedPyright, mypy, and upstream Pyright |
| `mise run test` | pytest with branch coverage |
| `mise run fuzz` | a larger 5000-example Hypothesis profile |
| `mise run bench -- '<expression>'` | pyperf timings |
| `mise run profile -- path/to/workload.py` | Pyinstrument sampling |
| `mise run build` | wheel and source distribution |
| `mise run outdated` | available dependency updates |

`pyrightconfig.json` configures BasedPyright, Pyright, and Pylance. mypy uses
`pyproject.toml`. Pylance runs in the editor; upstream Pyright checks its
analysis compatibility in CI. personal `.zed/`, `.vscode/`, and `AGENTS.md`
remain local, ignored, and excluded from distributions.

## checking a change

write the public use site and its types first. preserve meaningful None
payloads, lazy callbacks, shared cursors, and short-circuit remainders. use
focused examples and independent Hypothesis oracles for behavior and laws.
coverage locates missing paths; it has no enforced threshold and does not
prove correctness.

CI checks lint, typing, and builds. it runs Python 3.14 tests on Linux, macOS,
and Windows. `tests/conftest.py` registers reproducible CI and larger fuzz
profiles. run the required checks before committing; for documentation, also
execute examples and verify local links.

## measuring performance

use the tools directly, with a workload that represents the actual caller:

```sh
mise run bench -- --fast -s 'from kamo import Some; x = Some(42)' 'x.map(str)'
mise run profile -- path/to/workload.py
```

for a comparison, validate equal outputs, callback counts, error behavior, and
remaining source inputs before timing. compare against a strong direct Python
loop. separate the cost of wrappers from traversal, parsing, and output
construction. measure empty, small, and larger workloads when setup costs
could change the choice.

run timing experiments sequentially, without competing tests or profiles.
retain interpreter versions, JIT state, sample counts, and variation. profile
separately to identify the work behind a timing difference. an opcode sample
or allocation peak has a different meaning from elapsed time; report it as
such. check behavior and types after applying a candidate.

keep experimental scripts, raw results, and profiles outside the checkout or
in ignored local directories. commit runtime changes, focused tests, and API
documentation. the library stays pure Python with no runtime dependencies.
