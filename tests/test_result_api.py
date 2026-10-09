from collections.abc import Callable
from typing import Never, assert_type

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kamo import Err, Nothing, NothingType, Ok, Option, Result, Some


def test_predicates_and_option_conversion() -> None:
    calls: list[object] = []

    def predicate(payload: object) -> bool:
        calls.append(payload)
        return payload is None

    assert Ok(None).is_ok_and(predicate)
    assert not Ok(None).is_err_and(predicate)
    assert not Err(None).is_ok_and(predicate)
    assert Err(None).is_err_and(predicate)
    assert calls == [None, None]
    assert Ok(None).ok() == Some(None)
    assert Ok(None).err() is Nothing
    assert Err(None).ok() is Nothing
    assert Err(None).err() == Some(None)


def test_unwrapping_and_fallbacks() -> None:
    success, failure = Ok(0), Err("bad input")
    assert success.unwrap() == 0
    assert success.expect("required") == 0
    assert failure.unwrap_err() == "bad input"
    assert failure.expect_err("required") == "bad input"
    assert success.unwrap_or("missing") == 0
    assert failure.unwrap_or("missing") == "missing"
    calls: list[str] = []

    def default(error: str) -> int:
        calls.append(error)
        return len(error)

    assert success.unwrap_or_else(default) == 0
    assert calls == []
    assert failure.unwrap_or_else(default) == 9
    assert calls == ["bad input"]
    for unwrap, message in (
        (failure.unwrap, "called unwrap on Err: 'bad input'"),
        (success.unwrap_err, "called unwrap_err on Ok: 0"),
        (lambda: failure.expect("required"), "required: 'bad input'"),
        (lambda: success.expect_err("required"), "required: 0"),
    ):
        with pytest.raises(ValueError) as caught:
            unwrap()
        assert str(caught.value) == message


def test_mapping_inspection_and_laziness() -> None:
    success, failure = Ok(2), Err("bad")
    calls: list[object] = []

    def transform(value: int) -> str:
        calls.append(value)
        return str(value)

    def fix(error: str) -> int:
        calls.append(error)
        return len(error)

    def observe(payload: object) -> None:
        calls.append(payload)

    assert failure.map(transform) is failure
    assert success.map_err(fix) is success
    assert failure.inspect(observe) is failure
    assert success.inspect_err(observe) is success
    assert success.map_or_else(fix, transform) == "2"
    assert failure.map_or("default", transform) == "default"
    assert calls == [2]
    calls.clear()
    assert success.map(transform) == Ok("2")
    assert failure.map_err(fix) == Err(3)
    assert success.map_or("default", transform) == "2"
    assert failure.map_or_else(fix, transform) == 3
    assert success.inspect(observe) is success
    assert failure.inspect_err(observe) is failure
    assert calls == [2, "bad", 2, "bad", 2, "bad"]


def test_composition_preserves_selected_wrappers() -> None:
    success, failure = Ok(2), Err("bad")
    other_success, other_failure = Ok("next"), Err(404)
    assert success.and_(other_success) is other_success
    assert success.and_(other_failure) is other_failure
    assert failure.and_(other_success) is failure
    assert failure.and_(other_failure) is failure
    assert success.or_(other_success) is success
    assert success.or_(other_failure) is success
    assert failure.or_(other_success) is other_success
    assert failure.or_(other_failure) is other_failure
    calls: list[object] = []

    def step(value: int) -> Result[str, int]:
        calls.append(value)
        return other_success

    def recover(error: str) -> Result[str, int]:
        calls.append(error)
        return other_failure

    assert failure.and_then(step) is failure
    assert success.or_else(recover) is success
    assert calls == []
    assert success.and_then(step) is other_success
    assert failure.or_else(recover) is other_failure
    assert calls == [2, "bad"]


def test_flatten_and_transpose() -> None:
    success, failure = Ok(1), Err("bad")
    assert Ok(success).flatten() is success
    assert Ok(failure).flatten() is failure
    assert failure.flatten() is failure
    payload: list[int] = []
    transposed = Ok(Some(payload)).transpose()
    assert transposed.is_some is True
    assert transposed.value.value is payload
    assert Ok(Some(None)).transpose() == Some(Ok(None))
    assert Ok(Nothing).transpose() is Nothing
    transposed_error = failure.transpose()
    assert transposed_error.value is failure


def test_callback_exceptions_propagate_unchanged() -> None:
    error = RuntimeError("bug")

    def fail(payload: object) -> Never:
        raise error

    operations: list[Callable[[], object]] = [
        lambda: Ok(1).map(fail),
        lambda: Err("bad").map_err(fail),
        lambda: Ok(1).map_or(None, fail),
        lambda: Ok(1).map_or_else(fail, fail),
        lambda: Err("bad").map_or_else(fail, fail),
        lambda: Ok(1).inspect(fail),
        lambda: Err("bad").inspect_err(fail),
        lambda: Ok(1).and_then(fail),
        lambda: Err("bad").or_else(fail),
        lambda: Err("bad").unwrap_or_else(fail),
        lambda: Ok(1).is_ok_and(fail),
        lambda: Err("bad").is_err_and(fail),
    ]
    for operation in operations:
        with pytest.raises(RuntimeError) as caught:
            operation()
        assert caught.value is error


@given(st.integers(), st.booleans())
def test_result_laws(value: int, succeeds: bool) -> None:
    result: Result[int, str] = Ok(value) if succeeds else Err(str(value))

    def first(number: int) -> Result[int, str]:
        return Ok(number // 2) if number % 2 == 0 else Err("odd")

    def second(number: int) -> Result[int, str]:
        return Ok(number + 1) if number >= 0 else Err("negative")

    assert result.map(lambda x: x) == result
    assert result.map(str).map(len) == result.map(lambda x: len(str(x)))
    assert result.map_err(lambda x: x) == result
    assert result.map_err(len).map_err(str) == result.map_err(
        lambda x: str(len(x))
    )
    assert Ok(value).and_then(first) == first(value)
    assert result.and_then(Ok) == result
    assert result.and_then(first).and_then(second) == result.and_then(
        lambda x: first(x).and_then(second)
    )
    assert result.unwrap_or(None) == (value if succeeds else None)
    assert list(result) == ([value] if succeeds else [])


def test_public_types() -> None:
    def use(result: Result[int, str]) -> None:
        def widen(value: Result[object, object]) -> Result[object, object]:
            return value

        assert_type(widen(result), Result[object, object])
        assert_type(result.map(str), Result[str, str])
        assert_type(result.map_err(len), Result[int, int])
        assert_type(result.unwrap_or(None), int | None)
        assert_type(result.unwrap_or_else(len), int)
        assert_type(result.map_or(None, str), str | None)
        assert_type(result.map_or_else(len, str), int | str)
        converted: Option[int] = result.ok()
        errors: Option[str] = result.err()
        assert list(converted) == list(result)
        assert list(errors) == ([] if result.is_ok else [result.unwrap_err()])
        if result.is_ok is True:
            assert_type(result, Ok[int])
            assert_type(result.value, int)
        if result.is_err is True:
            assert_type(result, Err[str])
            assert_type(result.error, str)

    use(Ok(2))
    use(Err("bad"))
    assert_type(Ok(1).map(str), Ok[str])
    assert_type(Err("bad").map_err(len), Err[int])
    assert_type(Ok(1).map_err(str), Ok[int])
    assert_type(Err("bad").map(str), Err[str])
    assert_type(Ok(1).and_(Err("bad")), Err[str])
    assert_type(Err("bad").or_(Ok(1)), Ok[int])
    assert_type(Ok(1).and_then(lambda value: Err(str(value))), Err[str])
    assert_type(Err("bad").or_else(lambda error: Ok(len(error))), Ok[int])
    assert_type(Ok(Err("bad")).flatten(), Err[str])
    assert_type(Ok(Ok(1)).flatten(), Ok[int])
    assert_type(Ok(Some(1)).transpose(), Some[Ok[int]])
    assert_type(Ok(Nothing).transpose(), NothingType)

    def compose(result: Result[int, str]) -> None:
        def next_step(value: int) -> Result[float, bytes]:
            return Ok(float(value)) if value >= 0 else Err(b"negative")

        chained: Result[float, str | bytes] = result.and_then(next_step)
        recovered: Result[int | float, bytes] = result.or_else(
            lambda error: next_step(len(error))
        )
        assert chained == (
            next_step(result.value) if result.is_ok is True else result
        )
        assert recovered == (
            result if result.is_ok is True else next_step(len(result.error))
        )

    compose(Ok(2))
    compose(Err("bad"))
