"""read one blank-line-delimited section of key=value entries."""

from kamo import Err, Iter, Nothing, Ok, Option, Result, Some

type Entry = tuple[str, str]


def parse_entry(line: str) -> Option[Result[Entry, str]]:
    text = line.strip()
    if not text:
        return Nothing
    key, separator, value = text.partition("=")
    key = key.strip()
    return Some(
        Ok((key, value.strip()))
        if separator and key
        else Err(f"invalid entry: {text!r}")
    )


def read_section(lines: Iter[str]) -> tuple[dict[str, str], list[str]]:
    """consume a section; retain errors and let the last duplicate key win."""
    settings: dict[str, str] = {}
    errors: list[str] = []
    for entry in lines.map_while(parse_entry):
        if entry.is_ok is True:
            key, value = entry.value
            settings[key] = value
        else:
            errors.append(entry.error)
    return settings, errors
