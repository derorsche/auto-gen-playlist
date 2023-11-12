from collections.abc import Callable
from functools import wraps
from logging import getLogger
from time import sleep
from typing import ParamSpec, TypeVar

from spotipy import SpotifyException

T = TypeVar("T")
P = ParamSpec("P")

logger = getLogger(__name__)


class AGPException(Exception):
    pass


def automatic_retry(func: Callable[P, T]) -> Callable[P, T | None]:
    """関数が`SpotifyException`を送出した場合に、クールダウンを入れて自動的に再試行します。3回失敗したときは、`None`を返します。"""

    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs):
        for _ in range(3):
            try:
                return func(*args, **kwargs)
            except SpotifyException as err:
                logger.error(f"{func.__name__}({args=}, {kwargs=}) failed: {err}")
                sleep(1.5)
        logger.error(
            f"{func.__name__}({args=}, {kwargs=}) failed for 3 times. Process skipped."
        )

    return inner
