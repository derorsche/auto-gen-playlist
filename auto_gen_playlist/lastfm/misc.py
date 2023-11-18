from collections.abc import Callable, Sequence
from logging import getLogger
from typing import TypeVar, overload

T = TypeVar("T")  # actually T must be SupportsRichComparisonT
_T = TypeVar("_T")

logger = getLogger(__name__)


class AGPLException(Exception):
    pass


@overload
def bisect_left_with_descending(
    a: Sequence[T], x: T, lo: int = ..., hi: int | None = ..., *, key: None = ...
) -> int:
    ...


@overload
def bisect_left_with_descending(
    a: Sequence[_T],
    x: T,
    lo: int = ...,
    hi: int | None = ...,
    *,
    key: Callable[[_T], T] = ...,
) -> int:
    ...


def bisect_left_with_descending(
    a: Sequence[T] | Sequence[_T],
    x: T | _T,
    lo: int = 0,
    hi: int | None = None,
    *,
    key: Callable[[_T], T] | None = None,
) -> int:
    if lo < 0:
        raise ValueError("lo must be non-negative")
    if hi is None:
        hi = len(a)
    # Note, the comparison uses "<" to match the
    # __lt__() logic in list.sort() and in heapq.
    if key is None:
        while lo < hi:
            mid = (lo + hi) // 2
            logger.debug(f"{lo=}, {mid=}, {hi=}")
            if a[mid] < x:  # type: ignore
                hi = mid
            else:
                lo = mid + 1
    else:
        while lo < hi:
            mid = (lo + hi) // 2
            if key(a[mid]) < x:  # type: ignore
                hi = mid
            else:
                lo = mid + 1
    return lo
