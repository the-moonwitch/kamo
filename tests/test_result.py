from collections.abc import Iterator
from copy import copy, deepcopy
from dataclasses import FrozenInstanceError, replace
from operator import length_hint
from pickle import HIGHEST_PROTOCOL, dumps, loads
from types import GenericAlias
from typing import (
    Never,
    TypeVar,
    assert_never,
    assert_type,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

import pytest

from kamokamo import Err, Ok, Result


@pytest.mark.parametrize("payload", [None, False, 0, "", []])
def test_falsey_payloads_retain_their_variant(payload: object) -> None:
    assert Ok(value=payload).value is payload
    assert Err(error=payload).error is payload


def test_variant_identity_and_frozen_slots() -> None:
    def equal(left: object, right: object) -> bool:
        return left == right

    assert equal(Ok(1), Ok(1))
    assert equal(Err(1), Err(1))
    assert not equal(Ok(1), Err(1))
    assert not equal(Ok(1), 1)
    assert not equal(Err(1), (1,))
    assert repr(Ok("value")) == "Ok('value')"
    assert repr(Err("error")) == "Err('error')"
    assert len({Ok(1), Err(1)}) == 2
    for result, field in ((Ok(None), "value"), (Err(None), "error")):
        assert not hasattr(result, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(result, field, object())


def test_truth_does_not_evaluate_payload() -> None:
    class Payload:
        def __bool__(self) -> bool:
            raise AssertionError("payload truth was evaluated")

    assert bool(Ok(Payload())) is True
    assert bool(Err(Payload())) is False
    assert bool(Ok(False)) is True
    assert bool(Err(True)) is False


def test_constructor_and_pattern_types() -> None:
    def construct(value: int, error: str) -> tuple[Ok[int], Err[str]]:
        ok, err = Ok(value=value), Err(error=error)
        assert_type(ok, Ok[int])
        assert_type(err, Err[str])
        return ok, err

    def match_payload(result: Result[int, str]) -> int | str:
        match result:
            case Ok(value):
                assert_type(value, int)
                return value
            case Err(error):
                assert_type(error, str)
                return error
        assert_never(result)

    ok, err = construct(42, "failed")
    assert match_payload(ok) == 42
    assert match_payload(err) == "failed"


def test_fresh_copy_and_keyword_replacement() -> None:
    ok, err = Ok(value=[1]), Err(error=[1])
    for ok_clone in (ok.__copy__(), type(ok).__copy__(ok), copy(ok)):
        assert_type(ok_clone, Ok[list[int]])
        assert ok_clone is not ok and ok_clone.value is ok.value
    for err_clone in (err.__copy__(), type(err).__copy__(err), copy(err)):
        assert_type(err_clone, Err[list[int]])
        assert err_clone is not err and err_clone.error is err.error
    assert replace(ok, value=[2]) == Ok([2])
    assert replace(err, error=[2]) == Err([2])


def test_generic_construction_and_metadata() -> None:
    ok, err = Ok[int](value=1), Err[str](error="failed")
    assert_type(ok, Ok[int])
    assert_type(err, Err[str])
    assert not hasattr(ok, "__orig_class__")
    assert not hasattr(err, "__orig_class__")
    assert isinstance(Ok[int], GenericAlias)
    assert isinstance(Err[str], GenericAlias)
    assert get_origin(Ok[int]) is Ok and get_args(Ok[int]) == (int,)
    assert get_origin(Err[str]) is Err and get_args(Err[str]) == (str,)
    assert get_args(Ok[None]) == get_args(Err[None]) == (type(None),)

    parameter = TypeVar("parameter")
    ok_alias = Ok.__class_getitem__(parameter)[int]
    err_alias = Err.__class_getitem__(parameter)[str]
    assert get_origin(ok_alias) is Ok and get_args(ok_alias) == (int,)
    assert get_origin(err_alias) is Err and get_args(err_alias) == (str,)
    ok_factory = cast("type[Ok[int]]", ok_alias)
    err_factory = cast("type[Err[str]]", err_alias)
    assert ok_factory(value=2) == Ok(2)
    assert err_factory(error="specialized") == Err("specialized")

    def annotated(value: Ok[int]) -> Err[None]:
        return Err(None)

    hints = get_type_hints(annotated)
    assert get_args(hints["value"]) == (int,)
    assert get_args(hints["return"]) == (type(None),)
    restored_ok = cast("type[Ok[int]]", loads(dumps(Ok[int])))
    restored_err = cast("type[Err[str]]", loads(dumps(Err[str])))
    assert get_origin(restored_ok) is Ok
    assert get_origin(restored_err) is Err
    assert restored_ok(value=3) == Ok(3)
    assert restored_err(error="restored") == Err("restored")


def test_unhashable_generic_parameter() -> None:
    class UnhashableType(type):
        def __hash__(cls) -> int:
            raise TypeError("unhashable type")

    class Payload(metaclass=UnhashableType):
        pass

    payload = Payload()
    ok, err = Ok[Payload](value=payload), Err[Payload](error=payload)
    assert_type(ok, Ok[Payload])
    assert_type(err, Err[Payload])
    assert ok.value is payload and err.error is payload
    assert get_args(Ok[Payload]) == get_args(Err[Payload]) == (Payload,)


def test_deepcopy_preserves_graph_and_memo() -> None:
    for variant in ("ok", "err"):
        child: list[object] = []
        payload: list[object] = [child, child]
        result: Result[list[object], list[object]] = (
            Ok(payload) if variant == "ok" else Err(payload)
        )
        payload.append(result)
        child.append(child)
        cloned = deepcopy(result)
        cloned_payload = (
            cloned.value if isinstance(cloned, Ok) else cloned.error
        )
        assert cloned is not result and cloned_payload is not payload
        assert cloned_payload[0] is cloned_payload[1]
        assert cloned_payload[0] is not child
        assert cloned_payload[2] is cloned
        cloned_child = cloned_payload[0]
        assert isinstance(cloned_child, list)
        assert cloned_child[0] is cloned_child

        replacement: list[object] = ["replacement"]
        memo: dict[int, object] = {id(payload): replacement}
        replaced = deepcopy(result, memo)
        replaced_payload = (
            replaced.value if isinstance(replaced, Ok) else replaced.error
        )
        assert replaced_payload is replacement
        assert memo[id(result)] is replaced
        assert deepcopy(result, memo) is replaced


@pytest.mark.parametrize("protocol", range(HIGHEST_PROTOCOL + 1))
def test_pickle_variants_and_cycles(protocol: int) -> None:
    for flat_result in (Ok(None), Err(None), Ok(False), Err("failed")):
        restored = loads(dumps(flat_result, protocol))
        assert type(restored) is type(flat_result)
        assert restored == flat_result and restored is not flat_result
    for variant in ("ok", "err"):
        child: list[object] = []
        payload: list[object] = [child, child]
        result: Result[list[object], list[object]] = (
            Ok(payload) if variant == "ok" else Err(payload)
        )
        payload.append(result)
        restored = cast(
            "Result[list[object], list[object]]",
            loads(dumps(result, protocol)),
        )
        restored_payload = (
            restored.value if isinstance(restored, Ok) else restored.error
        )
        assert type(restored) is type(result) and restored is not result
        assert restored_payload is not payload
        assert restored_payload[0] is restored_payload[1]
        assert restored_payload[0] is not child
        assert restored_payload[2] is restored


def test_pickle_loads_previous_list_state() -> None:
    # protocol 4 list-state records with the current module name.
    fixtures = (
        (
            b'\x80\x04\x95"\x00\x00\x00\x00\x00\x00\x00'
            b"\x8c\x0fkamokamo.result\x94\x8c\x02Ok\x94\x93\x94)\x81"
            b"\x94]\x94Nab.",
            Ok(None),
        ),
        (
            b"\x80\x04\x95+\x00\x00\x00\x00\x00\x00\x00"
            b"\x8c\x0fkamokamo.result\x94\x8c\x03Err\x94\x93\x94)\x81"
            b"\x94]\x94\x8c\x06failed\x94ab.",
            Err("failed"),
        ),
    )
    for blob, expected in fixtures:
        restored = loads(blob)
        assert type(restored) is type(expected) and restored == expected


def test_iteration_is_fresh_and_success_only() -> None:
    sentinel = object()
    ok, err = Ok[None](None), Err[None](None)
    first, second = iter(ok), ok.iter()
    assert first is not second
    assert next(first, sentinel) is None
    assert next(second, sentinel) is None
    assert next(first, sentinel) is next(second, sentinel) is sentinel
    first_error, second_error = iter(err), err.iter()
    assert first_error is not second_error
    assert (
        next(first_error, sentinel) is next(second_error, sentinel) is sentinel
    )
    assert length_hint(err, 100) == 0
    assert_type(Ok[int](1).iter(), Iterator[int])
    assert_type(err.iter(), Iterator[Never])
