import json
import os
from datetime import datetime
from logging import getLogger
from typing import Any, TypeVar
from urllib.parse import urlencode

from aiohttp import ClientError, ClientResponse

from auto_gen_playlist.lastfm.misc import AGPLException
from auto_gen_playlist.lastfm.requests import fetch_all, fetch_one
from auto_gen_playlist.vars import CACHE_DIR, JST

ROOT = "http://ws.audioscrobbler.com/2.0/?"
T = TypeVar("T")

logger = getLogger(__name__)


async def extract_tracks(resp: ClientResponse) -> list[dict[str, Any]]:
    res = await resp.json(encoding="utf-8")
    if "recenttracks" in res and "track" in res["recenttracks"]:
        return [
            track
            for track in res["recenttracks"]["track"]
            if not (
                "@attr" in track
                and "nowplaying" in track["@attr"]
                and track["@attr"]["nowplaying"] == "true"
            )
        ]
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
        "page": page,
        "from": int(since.timestamp()) if since is not None else "",
        "to": int(until.timestamp()) if until is not None else "",
        "extended": int(extended),
        "format": "json",
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
        limit=3,
    ):
        tracks.extend(res if res is not None else [])

    return tracks


async def extract_user_info(resp: ClientResponse) -> dict[str, Any]:
    res = await resp.json(encoding="utf-8")
    if "user" in res:
        return res["user"]
    else:
        logger.error(
            f"Unexpected api response in extract_user_info(): await resp.json(encoding='utf-8')={res}"  # noqa: E501
        )
        raise ClientError(f"Invalid API Response: await resp.json()={res}")


def generate_user_info_url(user: str):
    query = {
        "method": "user.getinfo",
        "user": user,
        "api_key": os.environ["LAST_FM_API_KEY"],
        "format": "json",
    }
    return ROOT + urlencode(query)


async def fetch_user_info(user: str):
    """指定したユーザーの情報を取得して返します。取得に失敗した場合には、`None`を返します。"""
    if res := await fetch_one(extract_user_info, generate_user_info_url(user)):
        return res
    else:
        logger.error(
            f"Failed to fetch user '{user}', probably '{user}' doesn't exists."
        )


def recursively_remove_elements(res: T) -> T:
    """`res`に含まれる辞書から、`image`と`streamable`をキーとする要素を削除します。"""
    if isinstance(res, dict):
        return {
            k: recursively_remove_elements(res[k])
            for k in res.keys()  # type: ignore
            if str(k) not in ("image", "streamable")
        }
    elif isinstance(res, list):
        return [recursively_remove_elements(c) for c in res]  # type: ignore
    else:
        return res


async def fetch_tracks_all(user: str, refetch: bool = False):
    """指定したユーザーの`scrobbles`をすべて取得します。この際、データ量削減のために、一部の情報は削除します。
    取得した`scrobbles`はキャッシュとして保存して再利用しますが、`refetch=True`を指定すれば、全データを再取得します。"""
    if res := await fetch_user_info(user) is None:
        # check if specified user exists
        return

    path = CACHE_DIR + f"/scrobbles/{user}.json"
    since = None
    if not refetch:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if "date" in cache[0] and "uts" in cache[0]["date"]:
                since = datetime.fromtimestamp(int(cache[0]["date"]["uts"]) + 1, tz=JST)
            else:
                logger.error(
                    f"Invalid cache data: '{path}' is maybe broken. Try refetch."
                )
                return

    res = recursively_remove_elements(await fetch_tracks(user, since))

    if not refetch:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                res.extend(json.load(f))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=4)


async def get_user_history(
    user: str, update: bool = False, refetch: bool = False
) -> list[dict[str, Any]]:
    """指定したユーザーの`scrobbles`のキャッシュを返します。`update=True`を指定した場合、先にキャッシュを更新します。
    これに加えて、`refetch=True`を指定したときは、キャッシュを破棄して全データを再取得します。
    キャッシュが存在しない場合や、`scrobbles`の取得に失敗した場合には、`None`を返します。"""
    path = CACHE_DIR + f"/scrobbles/{user}.json"

    if update:
        await fetch_tracks_all(user, refetch)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        return cache

    else:
        raise AGPLException(
            f"Failed to get_user_history({user=}, {update=}, {refetch=})"
        )
