from collections.abc import Callable, Iterator
from operator import length_hint

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kamo import Iter, Nothing, Peekable, Some


def test_lookahead_is_lazy_shared_and_retains_wrappers() -> None:
    reads: list[int | None] = []
    values = Iter([None, 0, 2, 3]).inspect(reads.append).peekable()
    cursor = iter(values)
    pipeline = values.map(str)
    assert reads == []
    assert values.peekable() is values
    first = values.peek()
    assert first == Some(None)
    assert values.peek() is first
    assert reads == [None]
    assert values.next() is first
    assert next(cursor) == 0
    assert values.peek() == Some(2)
    assert pipeline.next() == Some("2")
    assert values.collect() == [3]
    assert values.peek() is Nothing
    assert values.next() is Nothing
    assert pipeline.collect() == []
    assert reads == [None, 0, 2, 3]
    assert not hasattr(values, "__dict__")


def test_conditional_consumption_retains_rejected_items() -> None:
    values = Peekable([None, 0, 1])
    assert values.next_if(lambda value: value is not None) is Nothing
    first = values.peek()
    assert values.next_if_eq(None) is first
    assert values.next_if_eq(1) is Nothing
    assert values.next_if(lambda value: value == 0) == Some(0)
    assert values.next_if_eq(1) == Some(1)
    assert values.next_if_eq(1) is Nothing
    assert values.next_if(lambda value: True) is Nothing


def test_length_hint_accounts_for_buffered_items() -> None:
    values = Peekable([None, 0, 1])
    assert length_hint(values) == 3
    assert values.peek() == Some(None)
    assert length_hint(values) == 3
    assert values.next() == Some(None)
    assert length_hint(values) == 2
    assert values.next() == Some(0)
    assert values.peek() == Some(1)
    assert values.collect() == [1]
    assert length_hint(values) == 0
    assert values.next() is Nothing
    assert length_hint(values) == 0


def test_exhaustion_is_cached_and_callbacks_are_skipped() -> None:
    reads: list[int] = []

    class Source:
        def __iter__(self) -> Iterator[int]:
            return self

        def __next__(self) -> int:
            reads.append(1)
            raise StopIteration

    def unexpected(value: int) -> bool:
        pytest.fail("called a predicate after exhaustion")

    operations: tuple[Callable[[Peekable[int]], object], ...] = (
        lambda p: p.peek(),
        lambda p: p.next(),
        list,
    )
    for exhaust in operations:
        values = Peekable(Source())
        exhaust(values)
        assert values.peek() is Nothing
        assert values.next() is Nothing
        assert values.next_if(unexpected) is Nothing
        with pytest.raises(StopIteration):
            next(iter(values))
        assert values.collect() == []
    assert reads == [1, 1, 1]


def test_source_and_predicate_errors_remain_distinct_from_exhaustion() -> None:
    error: Exception = ValueError("callback failed")

    def reject(value: int) -> bool:
        raise error

    values = Peekable([1, 2])
    for predicate_error in (error, StopIteration("predicate stopped")):
        error = predicate_error
        with pytest.raises(type(error)) as caught:
            values.next_if(reject)
        assert caught.value is error
        assert values.peek() == Some(1)
    assert values.collect() == [1, 2]

    class InvalidEquality:
        def __eq__(self, other: object) -> bool:
            raise error

    equalities = Peekable([InvalidEquality()])
    with pytest.raises(type(error)) as caught:
        equalities.next_if_eq(None)
    assert caught.value is error
    assert equalities.peek().is_some

    class Source:
        def __iter__(self) -> Iterator[int]:
            return self

        def __next__(self) -> int:
            raise error

    error = ValueError("source failed")
    operations: tuple[Callable[[Peekable[int]], object], ...] = (
        lambda p: p.peek(),
        lambda p: p.next(),
        lambda p: next(iter(p)),
    )
    for operation in operations:
        with pytest.raises(ValueError) as caught:
            operation(Peekable(Source()))
        assert caught.value is error


@given(
    st.lists(st.one_of(st.none(), st.integers())),
    st.lists(st.sampled_from(["peek", "next", "python", "reject", "accept"])),
)
def test_lookahead_matches_a_sequence_cursor(
    items: list[int | None], actions: list[str]
) -> None:
    values = Peekable(items)
    position = 0
    for action in actions:
        expected = Some(items[position]) if position < len(items) else Nothing
        if action == "peek":
            assert values.peek() == expected
        elif action == "reject":
            assert values.next_if(lambda value: False) is Nothing
        else:
            if action == "python":
                assert list(values.take(1)) == list(expected)
            elif action == "accept":
                assert values.next_if(lambda value: True) == expected
            else:
                assert values.next() == expected
            position = min(position + 1, len(items))
        assert length_hint(values) == len(items) - position
    assert values.collect() == items[position:]


def test_integer_tokenizer_retains_delimiters_and_expected_failures() -> None:
    from kamo import Err, Ok, Result

    def integer(characters: Peekable[str]) -> Result[int, str]:
        first = characters.next_if(str.isdecimal).ok_or("expected an integer")
        if first.is_err is True:
            return first
        digits = [first.value]
        while (digit := characters.next_if(str.isdecimal)).is_some is True:
            digits.append(digit.value)
        return Ok(int("".join(digits)))

    characters = Iter("12+34?").peekable()
    assert integer(characters) == Ok(12)
    assert characters.peek() == Some("+")
    assert characters.next_if_eq("+") == Some("+")
    assert integer(characters) == Ok(34)
    assert integer(characters) == Err("expected an integer")
    assert characters.peek() == Some("?")
    assert characters.collect() == ["?"]
    assert integer(characters) == Err("expected an integer")
