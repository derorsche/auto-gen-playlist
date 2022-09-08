import os
from datetime import datetime
from logging import getLogger
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientError, ClientResponse

from auto_gen_playlist.requests import fetch_all, fetch_one

ROOT = "http://ws.audioscrobbler.com/2.0/?"

logger = getLogger(__name__)


async def extract_tracks(resp: ClientResponse) -> list[dict[str, Any]]:
    res = await resp.json(encoding="utf-8")
    if "recenttracks" in res and "track" in res["recenttracks"]:
        return res["recenttracks"]["track"]
    else:
        logger.error(
            f"Unexpected api response in extract_tracks(): await resp.json(encoding='utf-8')={res}"  # noqa: E501
        )
        raise ClientError(f"Invalid API Response: await resp.json()={res}")


async def extract_tracks_total_pages(resp: ClientResponse) -> int:
    res = await resp.json(encoding="utf-8")
    if "recenttracks" in res and "@attr" in res["recenttracks"]:
        return int(res["recenttracks"]["@attr"]["totalPages"])
    else:
        logger.error(
            f"Unexpected api response in extract_tracks(): await resp.json(encoding='utf-8')={res}"  # noqa: E501
        )
        raise ClientError(f"Invalid API Response: await resp.json()={res}")


def generate_tracks_url(
    user: str,
    page: int = 1,
    since: datetime | None = None,
    until: datetime | None = None,
    extended: bool = True,
):
    query = {
        "method": "user.getrecenttracks",
        "limit": 200,
        "user": user,
        "api_key": os.environ["LAST_FM_API_KEY"],
        "format": "json",
        "page": page,
        "from": int(since.timestamp()) if since is not None else "",
        "to": int(until.timestamp()) if until is not None else "",
        "extended": int(extended),
    }
    return ROOT + urlencode(query)


async def fetch_tracks(
    user: str, since: datetime | None = None, until: datetime | None = None
):
    """指定したユーザーの`scrobbles`をすべて取得して返します。期間を指定することもできます。
    取得に失敗した場合には、空リストを返します。"""
    max_pages = await fetch_one(
        extract_tracks_total_pages, generate_tracks_url(user, since=since, until=until)
    )

    tracks: list[dict[str, Any]] = []
    if max_pages is None:
        return tracks

    for res in await fetch_all(
        extract_tracks,
        [
            generate_tracks_url(user, page, since, until)
            for page in range(1, max_pages + 1)
        ],
        limit=2,
    ):
        tracks.extend(res if res is not None else [])

    return tracks
