from collections.abc import Iterable, Iterator
from typing import Never, assert_type

from kamo import Err, Iter, Nothing, NothingType, Ok, Option, Result, Some


def test_public_types() -> None:
    numbers = Iter([1, 2, 3])
    assert_type(numbers, Iter[int])
    assert_type(iter(numbers), Iterator[int])
    assert_type(numbers.map(str), Iter[str])
    assert_type(numbers.filter(lambda value: value > 0), Iter[int])
    assert_type(numbers.filter_map(lambda value: Some(str(value))), Iter[str])
    assert_type(numbers.map_while(lambda value: Some(str(value))), Iter[str])
    assert_type(numbers.map_while(lambda value: Nothing), Iter[Never])
    assert_type(Iter([None]).map_while(Some), Iter[None])
    assert_type(
        numbers.partition(lambda value: value > 0), tuple[list[int], list[int]]
    )
    assert_type(numbers.flat_map(lambda value: [str(value)]), Iter[str])
    assert_type(Iter([[1], [2]]).flatten(), Iter[int])
    assert_type(numbers.take(2).skip(1), Iter[int])
    assert_type(numbers.zip(["a"]), Iter[tuple[int, str]])
    assert_type(numbers.enumerate(), Iter[tuple[int, int]])
    assert_type(numbers.chain(["a"]), Iter[int | str])
    assert_type(numbers.inspect(print), Iter[int])
    assert_type(numbers.next(), Option[int])
    assert_type(numbers.find(lambda value: value > 0), Option[int])
    assert_type(numbers.find_map(lambda value: Some(str(value))), Option[str])
    assert_type(numbers.reduce(lambda left, right: left + right), Option[int])
    assert_type(numbers.fold("", lambda text, value: text + str(value)), str)
    assert_type(numbers.collect(), list[int])
    assert_type(numbers.count(), int)
    assert_type(numbers.last(), Option[int])
    assert_type(numbers.position(lambda value: value > 0), Option[int])
    assert_type(Iter([None]).last(), Option[None])
    assert_type(numbers.any(lambda value: value > 0), bool)
    assert_type(numbers.all(lambda value: value > 0), bool)
    assert_type(numbers.for_each(print), None)

    def positive(value: int) -> Result[int, str]:
        return Ok(value) if value > 0 else Err("nonpositive")

    def optional(value: int) -> Option[int]:
        return Some(value) if value > 0 else Nothing

    def narrow(value: Option[int], result: Result[int, str]) -> None:
        if value.is_some is True:
            assert_type(value, Some[int])
            assert_type(value.value, int)
        else:
            assert_type(value, NothingType)
        if result.is_ok is True:
            assert_type(result, Ok[int])
            assert_type(result.value, int)
        else:
            assert_type(result, Err[str])
            assert_type(result.error, str)

    narrow(Some(1), Ok(1))
    narrow(Nothing, Err("missing"))

    def accumulate(total: int, value: int) -> Result[int, str]:
        return Ok(total + value) if value > 0 else Err("nonpositive")

    def visit(value: int) -> Result[None, str]:
        return Ok(None) if value > 0 else Err("nonpositive")

    assert_type(
        Iter([1]).map(positive).collect_result(), Result[list[int], str]
    )
    assert_type(Iter([1]).map(optional).collect_option(), Option[list[int]])
    assert_type(Iter([1]).try_fold(0, accumulate), Result[int, str])
    assert_type(Iter([1]).try_for_each(visit), Result[None, str])
    assert_type(Iter([Some(None)]).collect_option(), Some[list[None]])
    assert_type(Iter([Ok(None)]).collect_result(), Ok[list[None]])
    assert_type(Iter([Nothing]).collect_option(), Option[list[Never]])
    assert_type(Iter([Err("bad")]).collect_result(), Result[list[Never], str])
    assert_type(Iter([1]).filter_map(lambda value: Nothing), Iter[Never])
    assert_type(Iter([1]).find_map(lambda value: Nothing), NothingType)
    assert_type(
        Iter([1]).try_fold(0, lambda total, value: Ok(total)),
        Result[int, Never],
    )
    assert_type(Iter([1]).try_for_each(lambda value: Ok(None)), Ok[None])

    def widen(values: Iterable[object]) -> Iterable[object]:
        return values

    assert_type(widen(Iter([1])), Iterable[object])

    def covariant(values: Iter[object]) -> Iter[object]:
        return values

    assert_type(covariant(Iter([1])), Iter[object])


def test_lookahead_and_state_types() -> None:
    from kamo import Peekable

    values = Iter([1, 2]).peekable()
    assert_type(values, Peekable[int])
    assert_type(values.peek(), Option[int])
    assert_type(values.next_if(lambda value: value > 0), Option[int])
    assert_type(values.next_if_eq(None), Option[int])
    assert_type(values.map(str), Iter[str])
    assert_type(values.nth(0), Option[int])
    assert_type(values.map_while(lambda value: Some(str(value))), Iter[str])
    assert_type(
        values.partition(lambda value: value > 0), tuple[list[int], list[int]]
    )
    assert_type(values.count(), int)
    assert_type(values.last(), Option[int])
    assert_type(values.position(lambda value: value > 0), Option[int])
    assert_type(values.take_while(lambda value: True), Iter[int])
    assert_type(values.skip_while(lambda value: False), Iter[int])
    assert_type(
        values.scan(0, lambda total, value: (total + value, Some(str(total)))),
        Iter[str],
    )
    assert_type(
        values.scan(0, lambda total, value: (total, Nothing)), Iter[Never]
    )

    def widen(values: Iter[object]) -> Iter[object]:
        return values

    def lookahead(values: Peekable[object]) -> Peekable[object]:
        return values

    assert_type(widen(Peekable([1])), Iter[object])
    assert_type(lookahead(Peekable([1])), Peekable[object])
