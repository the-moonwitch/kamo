from copy import copy, deepcopy
from dataclasses import FrozenInstanceError, replace
from pickle import HIGHEST_PROTOCOL, dumps, loads
from typing import Literal, assert_type, cast

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
    assert hash(Nothing) == hash(())
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
    shallow = copy(option)
    assert shallow is not option and shallow.value is option.value
    cloned = deepcopy(option)
    assert cloned == option
    assert cloned is not option
    assert cloned.value is not option.value
    assert replace(option, value=[2]) == Some([2])
    for clone in (copy(Nothing), deepcopy(Nothing)):
        assert clone == Nothing and clone is not Nothing


def test_deepcopy_graph_and_memo() -> None:
    child: list[object] = []
    payload: list[object] = [child, child]
    option = Some(payload)
    payload.append(option)
    child.append(child)
    cloned = deepcopy(option)
    assert cloned.value is not payload
    assert cloned.value[0] is cloned.value[1]
    assert cloned.value[0] is not child
    assert cloned.value[2] is cloned
    cloned_child = cloned.value[0]
    assert isinstance(cloned_child, list)
    assert cloned_child[0] is cloned_child

    replacement: list[object] = ["replacement"]
    memo: dict[int, object] = {id(payload): replacement}
    replaced = deepcopy(option, memo)
    assert replaced.value is replacement
    assert memo[id(option)] is replaced
    assert deepcopy(option, memo) is replaced


@pytest.mark.parametrize("protocol", range(HIGHEST_PROTOCOL + 1))
def test_pickle(protocol: int) -> None:
    payloads: tuple[object, ...] = (None, False, 0, "", [])
    for value in payloads:
        option = Some(value)
        restored = cast("Some[object]", loads(dumps(option, protocol)))
        assert type(restored) is Some
        assert restored == option and restored is not option
    empty: object = loads(dumps(Nothing, protocol))
    assert type(empty) is type(Nothing)
    assert empty == Nothing and empty is not Nothing

    child: list[object] = []
    payload: list[object] = [child, child]
    cyclic = Some(payload)
    payload.append(cyclic)
    cloned = cast("Some[list[object]]", loads(dumps(cyclic, protocol)))
    assert cloned.value is not payload
    assert cloned.value[0] is cloned.value[1]
    assert cloned.value[0] is not child
    assert cloned.value[2] is cloned
    field = "value"
    with pytest.raises(FrozenInstanceError):
        setattr(cloned, field, [])


def test_legacy_pickle_state() -> None:
    # protocol 4 records produced before the specialized state hooks.
    present = (
        b"\x80\x04\x95&\x00\x00\x00\x00\x00\x00\x00\x8c\x0bkamo.option"
        b"\x94\x8c\x04Some\x94\x93\x94)\x81\x94]\x94]\x94(K\x01Neab."
    )
    absent = (
        b'\x80\x04\x95"\x00\x00\x00\x00\x00\x00\x00\x8c\x0bkamo.option'
        b"\x94\x8c\x08_Nothing\x94\x93\x94)\x81\x94]\x94b."
    )
    assert loads(present) == Some([1, None])
    assert loads(absent) == Nothing
    assert dumps(Some([1, None]), 4) == present
    assert dumps(Nothing, 4) == absent


def test_state_restoration_consumes_one_value() -> None:
    option = Some("original")
    state = iter(("updated", "unused"))
    option.__setstate__(state)
    assert option.value == "updated"
    assert next(state) == "unused"
    option.__setstate__([])
    assert option.value == "updated"


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


def test_zip_with() -> None:
    calls: list[tuple[object, object]] = []
    payloads: tuple[object, ...] = (None, False, 0, "", [])

    def first(left: object, right: object) -> object:
        calls.append((left, right))
        return left

    for value in payloads:
        result = Some(value).zip_with(other=Some("right"), function=first)
        assert result.is_some is True and result.value is value
    assert calls == [(value, "right") for value in payloads]
    calls.clear()
    assert Some(None).zip_with(Nothing, first) is Nothing
    assert Nothing.zip_with(Some(None), first) is Nothing
    assert Nothing.zip_with(Nothing, first) is Nothing
    assert calls == []

    def fail(left: int, right: int) -> int:
        raise RuntimeError("bug")

    with pytest.raises(RuntimeError, match="bug"):
        Some(1).zip_with(Some(2), fail)


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
    assert option.zip_with(Some(2), lambda left, right: left + right) == (
        Some(value + 2) if value is not None else Nothing
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
        assert_type(
            option.zip_with(
                Some("two"), lambda number, text: f"{number}{text}"
            ),
            Option[str],
        )
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
    assert_type(copy(Some(1)), Some[int])
    assert_type(deepcopy(Some(1)), Some[int])
    assert_type(Some(1).unwrap_or(None), int)
    assert_type(Some(1).or_(Some("default")), Some[int])

    def unzip(pair: tuple[int, str]) -> None:
        assert_type(Some(pair).unzip(), tuple[Some[int], Some[str]])

    unzip((1, "two"))
    assert_type(Some(Some(1)).flatten(), Option[int])
    assert_type(from_optional(1), Option[int])
