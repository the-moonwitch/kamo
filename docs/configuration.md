# configuration reader

a small paddle through a stream of settings.

this example combines Option section boundaries with Result entry errors. a
blank line ends a section and is consumed; later lines remain available.
malformed entries accumulate ordered errors, and the last duplicate key wins.

the implementation below comes directly from the
[source file](https://github.com/the-moonwitch/kamo/blob/codex/scaffold/examples/configuration.py).
the usage guide shows [resource ownership and consecutive sections](guide.md#streams-and-resource-ownership).

```{literalinclude} ../examples/configuration.py
:language: python
```
