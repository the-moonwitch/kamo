from copy import copy, deepcopy
from dataclasses import FrozenInstanceError, replace
from typing import Literal, assert_type

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kamo import Nothing, Option, Some, from_optional


@pytest.mark.parametrize("value", [None, False, 0, "", []])
def test_present_falsey_values(value: object) -> None:
    option = Some(value)
    assert option.value is value
    assert option.unwrap() is value
    assert option.expect("missing") is value
    assert option.is_some and not option.is_none
    assert bool(option)
    assert list(option) == [value]
    assert list(option.iter()) == [value]


def test_absence_and_python_conversion() -> None:
    assert not Nothing
    assert Nothing.is_none and not Nothing.is_some
    assert list(Nothing) == []
    assert list(Nothing.iter()) == []
    assert from_optional(None) is Nothing
    assert from_optional(0) == Some(0)
    assert Some(1).map(lambda _: None) == Some(None)
    assert Nothing.to_optional() is None
    assert Some(None).to_optional() is None
    assert Some(1).to_optional() == 1
    with pytest.raises(ValueError, match="called unwrap on Nothing"):
        Nothing.unwrap()
    with pytest.raises(ValueError, match="missing name"):
        Nothing.expect("missing name")


def test_values_and_pattern_matching() -> None:
    assert Some(1) == Some(1)
    assert Some(1) != Some(2)

    def same_value(left: object, right: object) -> bool:
        return left == right

    assert not same_value(Some(1), 1)
    assert not same_value(Some(1), (1,))
    assert not same_value(Some(None), Nothing)
    assert hash(Some(1)) == hash(Some(1))
    assert {Nothing, Nothing} == {Nothing}
    assert repr(Some("text")) == "Some('text')"
    assert repr(Nothing) == "Nothing"
    assert not hasattr(Some(1), "__dict__")
    assert not hasattr(Nothing, "__dict__")
    field = "value"
    with pytest.raises(FrozenInstanceError):
        setattr(Some(1), field, 2)

    def match_value(option: Option[int]) -> int | None:
        match option:
            case Some(value):
                assert_type(value, int)
                return value
            case _:
                return None

    assert match_value(Some(42)) == 42
    assert match_value(Nothing) is None


def test_construction_and_reconstruction() -> None:
    option = Some(value=[1])
    assert copy(option) == option
    cloned = deepcopy(option)
    assert cloned == option
    assert cloned.value is not option.value
    assert replace(option, value=[2]) == Some([2])


def test_callbacks_and_identity() -> None:
    calls: list[int | str] = []

    def transform(value: int) -> str:
        calls.append(value)
        return str(value)

    def fallback() -> str:
        calls.append("fallback")
        return "default"

    def option_fallback() -> Option[str]:
        return Some(fallback())

    def predicate(value: int) -> bool:
        calls.append(value)
        return value > 0

    present = Some(1)
    assert present.unwrap_or("default") == 1
    assert present.unwrap_or_else(fallback) == 1
    assert present.or_else(option_fallback) is present
    assert calls == []
    assert Nothing.map(transform) is Nothing
    assert Nothing.and_then(lambda value: Some(transform(value))) is Nothing
    assert Nothing.filter(predicate) is Nothing
    assert Nothing.inspect(transform) is Nothing
    assert not Nothing.is_some_and(predicate)
    assert Nothing.is_none_or(predicate)
    assert Nothing.map_or("default", transform) == "default"
    assert calls == []
    assert present.map(transform) == Some("1")
    assert present.map_or("default", transform) == "1"
    assert present.map_or_else(fallback, transform) == "1"
    assert present.inspect(transform) is present
    assert present.filter(predicate) is present
    assert present.is_some_and(predicate)
    assert present.is_none_or(predicate)
    assert calls == [1] * 7
    assert Nothing.unwrap_or("default") == "default"
    assert Nothing.unwrap_or_else(fallback) == "default"
    assert Nothing.map_or_else(fallback, transform) == "default"
    assert Nothing.or_else(option_fallback) == Some("default")
    assert calls == [1] * 7 + ["fallback"] * 3
    assert Some(0).filter(predicate) is Nothing
    assert not Some(0).is_some_and(predicate)
    assert not Some(0).is_none_or(predicate)


def test_boolean_combinators_and_zip() -> None:
    left, right = Some(1), Some("two")
    assert left.and_(right) is right
    assert left.and_(Nothing) is Nothing
    assert Nothing.and_(right) is Nothing
    assert left.or_(right) is left
    assert left.or_(Nothing) is left
    assert Nothing.or_(right) is right
    assert Nothing.or_(Nothing) is Nothing
    assert left.xor(right) is Nothing
    assert left.xor(Nothing) is left
    assert Nothing.xor(right) is right
    assert Nothing.xor(Nothing) is Nothing
    assert left.zip(right) == Some((1, "two"))
    assert Some(None).zip(Some(0)) == Some((None, 0))
    assert left.zip(Nothing) is Nothing
    assert Nothing.zip(right) is Nothing
    assert Some((1, "two")).unzip() == (left, right)
    assert Nothing.unzip() == (Nothing, Nothing)
    assert Some(left).flatten() is left
    assert Some(Nothing).flatten() is Nothing
    assert Nothing.flatten() is Nothing
    assert left.and_then(lambda _: right) is right
    assert left.and_then(lambda _: Nothing) is Nothing


def test_callback_errors_propagate() -> None:
    def fail(_: int) -> str:
        raise RuntimeError("bug")

    with pytest.raises(RuntimeError, match="bug"):
        Some(1).map(fail)


@given(st.integers() | st.none())
def test_option_laws(value: int | None) -> None:
    option = from_optional(value)

    def step(value: int) -> Option[int]:
        return Some(value // 2) if value % 2 == 0 else Nothing

    assert list(option) == ([] if value is None else [value])
    assert option.map(lambda x: x) == option
    assert option.map(lambda x: x + 1).map(str) == option.map(
        lambda x: str(x + 1)
    )
    assert option.and_then(Some) == option
    if value is not None:
        assert Some(value).and_then(step) == step(value)
    assert option.and_then(step).and_then(step) == option.and_then(
        lambda x: step(x).and_then(step)
    )
    assert option.filter(lambda x: x % 2 == 0) == (
        Some(value) if value is not None and value % 2 == 0 else Nothing
    )


def test_public_types() -> None:
    def use(option: Option[int]) -> None:
        def widen(value: Option[object]) -> Option[object]:
            return value

        assert_type(widen(option), Option[object])
        assert_type(option.map(str), Option[str])
        assert_type(option.and_then(lambda x: Some(str(x))), Option[str])
        assert_type(option.unwrap_or("default"), int | str)
        assert_type(option.unwrap_or_else(str), int | str)
        assert_type(option.map_or(None, str), str | None)
        assert_type(option.map_or_else(lambda: None, str), str | None)
        eager: Option[int | str] = option.or_(Some("default"))
        lazy: Option[int | str] = option.or_else(lambda: Some("default"))
        pair: Option[tuple[int, str]] = option.zip(Some("two"))
        assert eager == lazy
        assert pair == (Some((option.unwrap(), "two")) if option else Nothing)
        assert_type(option.to_optional(), int | None)
        if option.is_some is True:
            assert_type(option, Some[int])
            assert_type(option.value, int)
        if option.is_none is False:
            assert_type(option, Some[int])
            assert_type(option.value, int)

    use(Some(1))
    use(Nothing)
    assert_type(Some(1).value, int)
    assert_type(Some(1).is_some, Literal[True])
    assert_type(Nothing.is_some, Literal[False])
    assert_type(Some(None).is_none, Literal[False])
    assert_type(Nothing.is_none, Literal[True])
    assert_type(Some(1).map(str), Some[str])
    assert_type(Some(1).unwrap_or(None), int)
    assert_type(Some(1).or_(Some("default")), Some[int])

    def unzip(pair: tuple[int, str]) -> None:
        assert_type(Some(pair).unzip(), tuple[Some[int], Some[str]])

    unzip((1, "two"))
    assert_type(Some(Some(1)).flatten(), Option[int])
    assert_type(from_optional(1), Option[int])
