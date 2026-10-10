from io import StringIO
from typing import assert_type

from examples.configuration import Entry, parse_entry, read_section
from kamokamo import Err, Iter, Nothing, Ok, Option, Result, Some


def test_configuration_sections_and_source_ownership() -> None:
    text = (
        "port=80\ninvalid\nport = 8080\n=bad\ntoken=a=b\nempty=\n\nnext=yes\n"
    )
    with StringIO(text) as source:
        lines = Iter(source)
        assert_type(parse_entry("port=80"), Option[Result[Entry, str]])
        assert_type(
            read_section(Iter[str]([])), tuple[dict[str, str], list[str]]
        )
        assert read_section(lines) == (
            {"port": "8080", "token": "a=b", "empty": ""},
            ["invalid entry: 'invalid'", "invalid entry: '=bad'"],
        )
        assert not source.closed
        assert read_section(lines) == ({"next": "yes"}, [])
        assert read_section(lines) == ({}, [])
        assert not source.closed
    assert source.closed
    assert parse_entry(" \n") is Nothing
    assert parse_entry(" key = value \n") == Some(Ok(("key", "value")))
    assert parse_entry("broken") == Some(Err("invalid entry: 'broken'"))
