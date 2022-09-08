from asyncio import Semaphore, Task, create_task, gather, sleep
from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any, TypeVar

from aiohttp import ClientError, ClientResponse, ClientSession, TCPConnector

T = TypeVar("T")

logger = getLogger(__name__)


async def _fetch(
    session: ClientSession,
    coro: Callable[[ClientResponse], Awaitable[T]],
    url: str,
    *args: Any,
    **kwargs: Any,
) -> T | None:
    for _ in range(5):
        try:
            resp = await session.get(url, *args, **kwargs)
            resp.raise_for_status()
        except ClientError as err:
            logger.error(f"session.get({url=}, {args=}, {kwargs=}) failed: {err}")
            await sleep(2.0)
        else:
            logger.debug(f"successfully fetched: {url=}")
            return await coro(resp)
    logger.error(
        f"session.get({url=}, {args=}, {kwargs=}) failed for 5 times. Process skipped."  # noqa: E501
    )


async def _fetch_with_semaphore(
    semaphore: Semaphore,
    session: ClientSession,
    coro: Callable[[ClientResponse], Awaitable[T]],
    url: str,
    *args: Any,
    **kwargs: Any,
) -> T | None:
    async with semaphore:
        return await _fetch(session, coro, url, *args, **kwargs)


async def fetch_all(
    coro: Callable[[ClientResponse], Awaitable[T]],
    urls: list[str],
    limit: int = 1,
    *args: Any,
    **kwargs: Any,
) -> list[T | None]:
    """`session.get(url, *args, **kwargs)`を、同時実行数`limit`で並行実行し、レスポンスを`coro`に渡した結果を返します。
    `coro`は`ClientResponse`のみを引数に取るコルーチン関数である必要があります。"""
    tasks: list[Task[T | None]] = []
    semaphore = Semaphore(limit)

    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        for url in urls:
            task = create_task(
                _fetch_with_semaphore(semaphore, session, coro, url, *args, **kwargs)
            )
            tasks.append(task)
        responses = await gather(*tasks)
        return responses


async def fetch_one(
    coro: Callable[[ClientResponse], Awaitable[T]], url: str, *args: Any, **kwargs: Any
) -> T | None:
    """`fetch_all()`の単独実行版のコルーチン関数です。"""
    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        return await _fetch(session, coro, url, *args, **kwargs)
