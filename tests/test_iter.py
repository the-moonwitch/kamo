from collections.abc import Callable, Iterator
from itertools import count
from operator import length_hint
from typing import Never

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kamo import Err, Iter, Nothing, Ok, Option, Result, Some


def test_pipeline_is_lazy_and_stops_without_overreading() -> None:
    events: list[tuple[str, int]] = []

    def source() -> Iterator[int]:
        for value in range(10):
            events.append(("read", value))
            yield value

    def increment(value: int) -> int:
        events.append(("map", value))
        return value + 1

    def even(value: int) -> bool:
        events.append(("filter", value))
        return value % 2 == 0

    pipeline = (
        Iter(source())
        .map(increment)
        .filter(even)
        .inspect(lambda value: events.append(("inspect", value)))
        .take(2)
    )
    assert events == []
    assert pipeline.collect() == [2, 4]
    assert events == [
        ("read", 0),
        ("map", 0),
        ("filter", 1),
        ("read", 1),
        ("map", 1),
        ("filter", 2),
        ("inspect", 2),
        ("read", 2),
        ("map", 2),
        ("filter", 3),
        ("read", 3),
        ("map", 3),
        ("filter", 4),
        ("inspect", 4),
    ]
    assert pipeline.next() is Nothing
    assert pipeline.collect() == []


def test_facade_and_adapters_share_one_cursor() -> None:
    source = Iter([None, 1, 2, 3])
    cursor = iter(source)
    assert iter(source) is cursor
    assert source.next() == Some(None)
    assert next(cursor) == 1
    doubled = source.map(lambda value: value * 2 if value else 0)
    assert doubled.next() == Some(4)
    assert source.next() == Some(3)
    assert doubled.next() is Nothing
    assert source.next() is Nothing
    assert list(source) == []
    assert not isinstance(source, Iterator)


def test_length_hint_tracks_remaining_items() -> None:
    values = Iter([0, 1, 2])
    assert length_hint(values) == 3
    assert values.next() == Some(0)
    assert length_hint(values) == 2
    assert list(values) == [1, 2]
    assert length_hint(values) == 0
    assert not hasattr(values, "__dict__")


def test_take_and_skip_boundaries() -> None:
    values = Iter(count())
    skipped = values.skip(3)
    assert values.next() == Some(0)
    assert skipped.take(2).collect() == [4, 5]
    assert values.next() == Some(6)
    assert values.take(0).collect() == []
    assert values.next() == Some(7)
    for operation in (values.take, values.skip):
        with pytest.raises(ValueError):
            operation(-1)
    assert values.next() == Some(8)
    assert Iter([1]).skip(5).next() is Nothing


def test_filter_map_preserves_none_and_operator_order() -> None:
    def choose(value: int) -> Option[int | None]:
        if value == 0:
            return Some(None)
        return Some(value) if value % 2 == 0 else Nothing

    assert Iter(range(8)).take(3).filter_map(choose).collect() == [None, 2]
    assert Iter(range(8)).filter_map(choose).take(3).collect() == [None, 2, 4]


def test_zip_consumption_matches_python() -> None:
    left = Iter([1, 2, 3])
    right = Iter(["a"])
    assert left.zip(right).collect() == [(1, "a")]
    # Python's zip consumes a left item before discovering the right is empty.
    assert left.next() == Some(3)
    assert right.next() is Nothing


def test_fold_reduce_and_empty_values() -> None:
    assert (
        Iter([1, 2, 3]).fold("", lambda text, value: text + str(value))
        == "123"
    )
    assert Iter[int]([]).fold(10, lambda total, value: total + value) == 10
    assert Iter([1, 2, 3]).reduce(lambda left, right: left - right) == Some(-4)
    assert Iter[int]([]).reduce(lambda left, right: left + right) is Nothing
    assert Iter([None, None]).reduce(lambda left, right: left) == Some(None)


def test_search_and_predicates_leave_the_remainder() -> None:
    values = Iter([0, 1, 2, 3, 4])
    assert values.find(lambda value: value > 0) == Some(1)
    assert values.any(lambda value: value % 2 == 0)
    assert not values.all(lambda value: value < 3)
    assert values.collect() == [4]
    assert not values.any(lambda value: True)
    assert values.all(lambda value: False)
    assert values.find(lambda value: True) is Nothing
    selected = Some(None)
    assert Iter([0, 1]).find_map(lambda value: selected) is selected
    assert Iter([0, 1]).find_map(lambda value: Nothing) is Nothing


def test_collect_result_stops_at_the_first_error() -> None:
    error = Err({"line": 2})
    seen: list[int] = []

    def parse(value: int) -> Result[int | None, dict[str, int]]:
        seen.append(value)
        return error if value == 2 else Ok(None if value == 0 else value)

    values = Iter(range(5)).map(parse)
    assert values.collect_result() is error
    assert seen == [0, 1, 2]
    assert values.collect_result() == Ok([3, 4])
    assert seen == [0, 1, 2, 3, 4]
    assert values.collect_result() == Ok([])
    assert Iter([Ok(None), Ok(False)]).collect_result() == Ok([None, False])


def test_collect_option_stops_at_absence() -> None:
    options: list[Option[int | None]] = [
        Some(None),
        Some(False),
        Nothing,
        Some(3),
    ]
    values = Iter(options)
    assert values.collect_option() is Nothing
    assert values.collect_option() == Some([3])
    assert values.collect_option() == Some([])
    assert Iter([Some(None), Some(False)]).collect_option() == Some(
        [None, False]
    )


def test_fallible_consumers_retain_error_identity_and_remainder() -> None:
    error = Err("stop")
    calls: list[tuple[int, int]] = []

    def add(total: int, value: int) -> Result[int, str]:
        calls.append((total, value))
        return error if value == 3 else Ok(total + value)

    values = Iter(range(1, 6))
    assert values.try_fold(0, add) is error
    assert calls == [(0, 1), (1, 2), (3, 3)]
    assert values.try_fold(0, add) == Ok(9)
    assert values.try_fold(10, add) == Ok(10)
    visits: list[int] = []

    def visit(value: int) -> Result[None, str]:
        visits.append(value)
        return error if value == 2 else Ok(None)

    values = Iter(range(5))
    assert values.try_for_each(visit) is error
    assert visits == [0, 1, 2]
    assert values.try_for_each(visit) == Ok(None)
    assert visits == [0, 1, 2, 3, 4]
    assert values.try_for_each(visit) == Ok(None)


def test_for_each_consumes_once_in_order() -> None:
    visits: list[int] = []
    inspected: list[int] = []
    values = Iter([3, 1, 2]).inspect(inspected.append)
    values.for_each(visits.append)
    values.for_each(visits.append)
    assert visits == inspected == [3, 1, 2]


def test_callback_errors_are_not_converted_to_results() -> None:
    error = ValueError("bug")

    def fail(*values: object) -> Never:
        raise error

    def fail_option(value: int) -> Option[int]:
        raise error

    def fail_iterable(value: int) -> Iterator[int]:
        raise error

    def fail_fold(total: int, value: int) -> Result[int, str]:
        raise error

    def fail_visit(value: int) -> Result[None, str]:
        raise error

    operations: list[Callable[[], object]] = [
        lambda: Iter([1]).map(fail).collect(),
        lambda: Iter([1]).filter(fail).collect(),
        lambda: Iter([1]).take_while(fail).collect(),
        lambda: Iter([1]).skip_while(fail).collect(),
        lambda: Iter([1]).filter_map(fail_option).collect(),
        lambda: Iter([1]).flat_map(fail_iterable).collect(),
        lambda: Iter([1]).inspect(fail).collect(),
        lambda: Iter([1]).fold(0, fail),
        lambda: Iter([1, 2]).reduce(fail),
        lambda: Iter([1]).find(fail),
        lambda: Iter([1]).find_map(fail_option),
        lambda: Iter([1]).any(fail),
        lambda: Iter([1]).all(fail),
        lambda: Iter([1]).for_each(fail),
        lambda: Iter([1]).try_fold(0, fail_fold),
        lambda: Iter([1]).try_for_each(fail_visit),
    ]
    for operation in operations:
        with pytest.raises(ValueError) as caught:
            operation()
        assert caught.value is error


def test_source_errors_propagate_without_becoming_absence() -> None:
    error = RuntimeError("source failed")

    def source() -> Iterator[int]:
        yield 1
        raise error

    values = Iter(source())
    assert values.next() == Some(1)
    with pytest.raises(RuntimeError) as caught:
        values.next()
    assert caught.value is error


@given(st.lists(st.integers()), st.integers(min_value=0, max_value=30))
def test_lazy_composition_matches_an_eager_oracle(
    values: list[int], limit: int
) -> None:
    expected = [value + 1 for value in values if (value + 1) % 2 == 0][:limit]
    assert (
        Iter(values)
        .map(lambda value: value + 1)
        .filter(lambda value: value % 2 == 0)
        .take(limit)
        .collect()
    ) == expected
    assert Iter(values).skip(limit).collect() == values[limit:]
    assert Iter(values).fold(0, lambda total, value: total + value) == sum(
        values
    )


@given(st.lists(st.lists(st.integers())), st.lists(st.text()))
def test_expansion_and_pairing_oracles(
    groups: list[list[int]], words: list[str]
) -> None:
    expected = [value for group in groups for value in group]
    assert Iter(groups).flatten().collect() == expected
    assert Iter(groups).flat_map(lambda group: group).collect() == expected
    assert Iter(expected).chain(words).collect() == expected + words
    assert Iter(words).enumerate(2).collect() == [
        (index + 2, word) for index, word in enumerate(words)
    ]


@given(st.lists(st.one_of(st.none(), st.integers())))
def test_fallible_collection_matches_first_failure_oracle(
    values: list[int | None],
) -> None:
    options: list[Option[int]] = [
        Nothing if value is None else Some(value) for value in values
    ]
    results: list[Result[int, str]] = [
        Err("missing") if value is None else Ok(value) for value in values
    ]
    successes = [value for value in values if value is not None]
    assert Iter(options).collect_option() == (
        Nothing if None in values else Some(successes)
    )
    assert Iter(results).collect_result() == (
        Err("missing") if None in values else Ok(successes)
    )


def test_prefix_adapters_and_nth_share_the_remaining_cursor() -> None:
    calls: list[int] = []

    def below_three(value: int) -> bool:
        calls.append(value)
        return value < 3

    values = Iter(range(6))
    prefix = values.take_while(below_three)
    assert calls == []
    assert prefix.collect() == [0, 1, 2]
    assert calls == [0, 1, 2, 3]
    assert values.next() == Some(4)
    assert prefix.next() is Nothing
    assert values.next() == Some(5)

    calls.clear()
    values = Iter([0, 1, 3, 2, 4])
    suffix = values.skip_while(below_three)
    assert calls == []
    assert suffix.collect() == [3, 2, 4]
    assert calls == [0, 1, 3]
    assert Iter(count()).skip_while(lambda x: x < 5).take(2).collect() == [
        5,
        6,
    ]

    optional_values = Iter([None, 1, 2, 3])
    with pytest.raises(ValueError):
        optional_values.nth(-1)
    assert optional_values.nth(0) == Some(None)
    assert optional_values.nth(1) == Some(2)
    assert optional_values.next() == Some(3)
    assert optional_values.nth(100) is Nothing


def test_scan_state_laziness_termination_and_errors() -> None:
    calls: list[tuple[int, int]] = []

    def accumulate(total: int, value: int) -> tuple[int, Option[int | None]]:
        calls.append((total, value))
        total += value
        return total, Some(
            None if total == 1 else total
        ) if total < 6 else Nothing

    values = Iter([1, 2, 3, 4])
    running = values.scan(0, accumulate)
    assert calls == []
    assert running.next() == Some(None)
    assert running.collect() == [3]
    assert calls == [(0, 1), (1, 2), (3, 3)]
    assert running.next() is Nothing
    assert values.collect() == [4]
    assert Iter[int]([]).scan(0, accumulate).collect() == []

    def fail(total: int, value: int) -> tuple[int, Option[int]]:
        raise ValueError("scan failed")

    values = Iter([1, 2])
    with pytest.raises(ValueError, match="scan failed"):
        values.scan(0, fail).collect()
    assert values.collect() == [2]


@given(st.lists(st.integers()), st.integers(min_value=0, max_value=100))
def test_prefix_scan_and_nth_sequence_oracles(
    items: list[int], index: int
) -> None:
    split = next((i for i, value in enumerate(items) if value < 0), len(items))
    assert (
        Iter(items).take_while(lambda value: value >= 0).collect()
        == items[:split]
    )
    assert (
        Iter(items).skip_while(lambda value: value >= 0).collect()
        == items[split:]
    )
    assert Iter(items).nth(index) == (
        Some(items[index]) if index < len(items) else Nothing
    )
    running: list[int] = []
    total = 0
    for value in items:
        total += value
        running.append(total)
    assert (
        Iter(items)
        .scan(0, lambda total, value: (total + value, Some(total + value)))
        .collect()
        == running
    )


def test_count_and_last_drain_the_remaining_items_and_callbacks() -> None:
    items: list[int | None] = [None, 0, 2, None]
    seen: list[int | None] = []
    values = Iter(items).inspect(seen.append)
    assert values.next() == Some(None)
    assert values.count() == 3
    assert seen == items
    assert values.count() == 0
    assert values.last() is Nothing

    seen.clear()
    values = Iter(items).inspect(seen.append)
    assert values.next() == Some(None)
    assert values.last() == Some(None)
    assert seen == items
    assert values.last() is Nothing
    assert values.count() == 0

    class NoHint(Iter[int]):
        def __length_hint__(self) -> int:
            raise AssertionError("a hint cannot replace consumption")

    assert NoHint([1, 2, 3]).count() == 3
    assert NoHint([1, 2, 3]).last() == Some(3)


def test_position_consumes_the_match_and_restarts_its_index() -> None:
    seen: list[int] = []
    values = Iter(count()).inspect(seen.append)
    assert values.position(lambda value: value == 2) == Some(2)
    assert seen == [0, 1, 2]
    assert values.position(lambda value: value == 3) == Some(0)
    assert values.next() == Some(4)
    assert values.position(lambda value: value == 6) == Some(1)
    assert values.next() == Some(7)
    assert seen == list(range(8))
    assert Iter([None]).position(lambda value: value is None) == Some(0)
    assert Iter([0]).position(lambda value: value != 0) is Nothing


def test_consumers_propagate_source_and_position_predicate_errors() -> None:
    error: Exception = ValueError("source failed")

    def source() -> Iterator[int]:
        yield 1
        raise error

    operations: tuple[Callable[[Iter[int]], object], ...] = (
        lambda values: values.count(),
        lambda values: values.last(),
        lambda values: values.position(lambda value: False),
    )
    for operation in operations:
        for advance in (False, True):
            values = Iter(source())
            if advance:
                assert values.next() == Some(1)
            with pytest.raises(ValueError) as caught:
                operation(values)
            assert caught.value is error

    def fail(value: int) -> bool:
        raise error

    for predicate_error in (error, StopIteration("predicate stopped")):
        error = predicate_error
        values = Iter([1, 2])
        with pytest.raises(type(error)) as predicate_caught:
            values.position(fail)
        assert predicate_caught.value is error
        assert values.next() == Some(2)


@given(
    st.lists(st.one_of(st.none(), st.integers())),
    st.integers(min_value=0, max_value=100),
    st.one_of(st.none(), st.integers()),
)
def test_count_last_and_position_match_remaining_sequence_oracles(
    items: list[int | None], skip: int, target: int | None
) -> None:
    remaining = items[skip:]
    assert Iter(items).skip(skip).count() == len(remaining)
    assert Iter(items).skip(skip).last() == (
        Some(remaining[-1]) if remaining else Nothing
    )
    values = Iter(items).skip(skip)
    if target in remaining:
        index = remaining.index(target)
        assert values.position(lambda value: value == target) == Some(index)
        assert values.collect() == remaining[index + 1 :]
    else:
        assert values.position(lambda value: value == target) is Nothing
        assert values.collect() == []


def test_map_while_is_lazy_and_stops_permanently_at_absence() -> None:
    calls: list[int] = []

    def choose(value: int) -> Option[int | None]:
        calls.append(value)
        return Nothing if value == 2 else Some(None if value == 0 else value)

    values = Iter(range(4))
    prefix = values.map_while(choose)
    assert calls == []
    assert prefix.collect() == [None, 1]
    assert calls == [0, 1, 2]
    assert prefix.next() is Nothing
    assert prefix.collect() == []
    assert calls == [0, 1, 2]
    assert values.next() == Some(3)
    assert Iter([1, 2]).map_while(lambda value: Nothing).collect() == []
    assert Iter[int]([]).map_while(choose).next() is Nothing
    assert calls == [0, 1, 2]


def test_partition_preserves_order_and_calls_the_predicate_once() -> None:
    seen: list[int | None] = []

    def present(value: int | None) -> bool:
        seen.append(value)
        return value is not None

    items: list[int | None] = [99, None, 0, None, 2, 0]
    values = Iter(items)
    assert values.next() == Some(99)
    assert values.partition(present) == ([0, 2, 0], [None, None])
    assert seen == items[1:]
    accepted, rejected = values.partition(present)
    assert accepted == rejected == []
    assert accepted is not rejected
    assert seen == items[1:]


def test_map_while_and_partition_errors_preserve_later_inputs() -> None:
    error = ValueError("callback failed")

    def fail(value: int) -> Never:
        raise error

    values = Iter([1, 2])
    prefix = values.map_while(fail)
    with pytest.raises(ValueError) as caught:
        prefix.next()
    assert caught.value is error
    assert prefix.next() is Nothing
    assert values.next() == Some(2)

    values = Iter([1, 2])
    with pytest.raises(ValueError) as caught:
        values.partition(fail)
    assert caught.value is error
    assert values.next() == Some(2)

    def stop(value: int) -> Never:
        raise StopIteration("callback stopped")

    with pytest.raises(RuntimeError, match="generator raised StopIteration"):
        Iter([1]).map_while(stop).next()
    with pytest.raises(StopIteration, match="callback stopped"):
        Iter([1]).partition(stop)

    def source() -> Iterator[int]:
        yield 1
        raise error

    with pytest.raises(ValueError) as caught:
        Iter(source()).map_while(Some).collect()
    assert caught.value is error
    with pytest.raises(ValueError) as caught:
        Iter(source()).partition(lambda value: True)
    assert caught.value is error


@given(st.lists(st.one_of(st.none(), st.integers())))
def test_map_while_and_partition_match_independent_sequence_oracles(
    items: list[int | None],
) -> None:
    # None is a stop marker in this callback, not in the iterator itself.
    split = items.index(None) if None in items else len(items)
    values = Iter(items)
    assert values.map_while(
        lambda value: Nothing if value is None else Some(str(value))
    ).collect() == [str(value) for value in items[:split]]
    assert values.collect() == items[min(split + 1, len(items)) :]
    assert Iter(items).partition(lambda value: value is None) == (
        [value for value in items if value is None],
        [value for value in items if value is not None],
    )
