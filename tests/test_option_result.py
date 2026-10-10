from collections.abc import Callable
from typing import Never, assert_type, get_type_hints

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kamo import Err, Nothing, NothingType, Ok, Option, Result, Some


def test_error_conversion_preserves_payloads_and_skips_factories() -> None:
    payload = object()
    error = object()
    assert Some(payload).ok_or(error).value is payload
    assert Nothing.ok_or(error).error is error
    assert Some(None).ok_or(error) == Ok(None)
    calls: list[int] = []

    def missing() -> object:
        calls.append(1)
        return error

    assert Some(False).ok_or_else(missing) == Ok(False)
    assert calls == []
    assert Nothing.ok_or_else(missing).error is error
    assert calls == [1]

    def fail() -> Never:
        raise ValueError("error factory failed")

    assert Some(0).ok_or_else(fail) == Ok(0)
    with pytest.raises(ValueError, match="error factory failed"):
        Nothing.ok_or_else(fail)


def test_transpose_preserves_errors_and_meaningful_none() -> None:
    error = Err(object())
    assert Some(error).transpose() is error
    assert Some(Ok(None)).transpose() == Ok(Some(None))
    assert Nothing.transpose() == Ok(Nothing)
    payload = object()
    assert Some(Ok(payload)).transpose().value.value is payload


@given(st.one_of(st.none(), st.integers()), st.booleans(), st.booleans())
def test_transpose_is_an_inverse(
    payload: int | None, present: bool, success: bool
) -> None:
    option: Option[Result[int | None, int | None]] = (
        Some(Ok(payload) if success else Err(payload)) if present else Nothing
    )
    assert option.transpose().transpose() == option
    result: Result[Option[int | None], int | None] = (
        Ok(Some(payload) if present else Nothing) if success else Err(payload)
    )
    assert result.transpose().transpose() == result


def test_bridge_types_and_runtime_annotations() -> None:
    assert_type(Some(None).ok_or("missing"), Ok[None])
    assert_type(Some(0).ok_or_else(str), Ok[int])
    assert_type(Nothing.ok_or("missing"), Err[str])
    assert_type(Nothing.ok_or_else(str), Err[str])
    assert_type(Some(Ok(None)).transpose(), Ok[Some[None]])
    assert_type(Some(Err("bad")).transpose(), Err[str])
    assert_type(Nothing.transpose(), Ok[NothingType])

    def convert(option: Option[int]) -> None:
        assert_type(option.ok_or("missing"), Result[int, str])
        assert_type(option.ok_or_else(str), Result[int, str])

    convert(Some(1))
    convert(Nothing)
    # deferred annotations remain introspectable across the two modules.
    methods: tuple[Callable[..., object], ...] = (
        Some(1).ok_or,
        Some(1).ok_or_else,
        Some(Ok(1)).transpose,
        Nothing.transpose,
        Ok(Some(1)).transpose,
        Err("bad").transpose,
    )
    for method in methods:
        assert get_type_hints(method)["return"] is not None
