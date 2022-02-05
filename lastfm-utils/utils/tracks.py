import asyncio
import csv
import os
import urllib.parse
from asyncio.locks import Semaphore
from datetime import datetime, timedelta, timezone
from typing import List, NamedTuple, Optional, Tuple

from aiohttp import ClientResponse, ClientResponseError, ClientSession

jst = timezone(timedelta(hours=9))


class Scrobble(NamedTuple):
    """
    last.fm の scrobble を扱うための NamedTuple です。時刻は UNIX 時間で保存します。
    - title: str = "Zombie"
    - artist: str = "The Cranberries"
    - album: str = "No Need To Argue (The Complete Sessions 1994-1995)"
    - time: int = 1636191690
    """

    title: str
    artist: str
    album: str
    time: int


async def fetch_and_process_url_in_session(
    session: ClientSession, url: str
) -> Optional[ClientResponse]:
    """
    渡された `session` の中で `url` を取得して返します。下記の場合には `None` を返します。
    - レスポンスエラーが発生した場合、クールダウンを入れて 5回まで再試行しますが、6回目に `None` を渡します。
    - `session.get()` がタイムアウトした場合、`None` を渡します。
    """

    headers = {"user-agent": os.environ["user-agent"]}
    count = 0
    resp = None

    while count < 5:
        try:
            resp = await session.get(url, headers=headers, raise_for_status=True)
            break
        except ClientResponseError:
            count += 1
            await asyncio.sleep(2)

    return resp


async def fetch_recent_tracks_in_session(
    session: ClientSession,
    username: str,
    page: int = 1,
    since: datetime = datetime(1970, 1, 1, tzinfo=jst),
    until: datetime = datetime(2040, 1, 1, tzinfo=jst),
) -> Tuple[int, List[Scrobble]]:
    """
    `user.getRecentTracks` のラッパーです。第一引数に総ページ数、第二引数に取得した `Scrobble` のリストを返します。
    """

    query = {
        "method": "user.getrecenttracks",
        "limit": 200,
        "user": username,
        "api_key": os.environ["api-key"],
        "format": "json",
        "page": page,
        "from": int(since.timestamp()),
        "to": int(until.timestamp()),
    }
    root = "http://ws.audioscrobbler.com/2.0/?"

    url = root + urllib.parse.urlencode(query)

    resp = await fetch_and_process_url_in_session(session, url)
    return await convert_resp_to_scrobbles(resp)


async def convert_resp_to_scrobbles(
    resp: Optional[ClientResponse],
) -> Tuple[int, List[Scrobble]]:
    """
    `user.getRecentTracks` のレスポンスを整形するコルーチンです。`None` が渡されたときは、`(0, [])` を返します。
    """
    if resp is not None:
        res = await resp.json()
        scrobbles = []

        for track in res["recenttracks"]["track"]:
            if "date" not in track:
                continue
            else:
                scrobbles.append(
                    Scrobble(
                        track["name"],
                        track["artist"]["#text"],
                        track["album"]["#text"],
                        int(track["date"]["uts"]),
                    )
                )

        return (int(res["recenttracks"]["@attr"]["totalPages"]), scrobbles)

    else:
        return (0, [])


async def fetch_scrobbles_with_semaphore(
    session: ClientSession,
    semaphore: Semaphore,
    username: str,
    page: int = 1,
    since: datetime = datetime(1970, 1, 1, tzinfo=jst),
    until: datetime = datetime(2040, 1, 1, tzinfo=jst),
) -> List[Scrobble]:
    """
    `semaphore` で並列実行数を制限しながら `scrobbles` を取得するためのコルーチンです。
    """
    async with semaphore:
        res = await fetch_recent_tracks_in_session(
            session, username, page, since, until
        )
        if page % 20 == 0:
            print(f"fetched scrobbles of page {page}.")
        return res[1]


async def fetch_all_scrobbles(
    username: str,
    since: datetime = datetime(1970, 1, 1, tzinfo=jst),
    until: datetime = datetime(2040, 1, 1, tzinfo=jst),
) -> List[Scrobble]:
    """
    指定したユーザーの `scrobble` をすべて取得して返します。期間を指定することもできます。
    """
    async with ClientSession() as session:
        res = await fetch_recent_tracks_in_session(session, username, 1, since, until)

        semaphore = Semaphore(3)
        tasks = [
            asyncio.ensure_future(
                fetch_scrobbles_with_semaphore(
                    session, semaphore, username, page, since, until
                )
            )
            for page in range(2, res[0] + 1)
        ]

        scrobbles_list = await asyncio.gather(*tasks)

    for content in scrobbles_list:
        res[1].extend(content)

    return res[1]


async def update_or_fetch_scrobbles(username: str, update: bool = True) -> None:
    """
    指定したユーザーの `scrobble` をすべて取得し、`data/scrobbles/{username}_scrobbles.csv` に保存します。
    すでに `{username}_scrobbles.csv` が存在する場合、それ以降の `scrobble` だけを取得して追加しますが、
    `update` に `False` を渡した場合には、取得済の `scrobble` を破棄して新しく取得します。
    """

    os.makedirs("data/scrobbles/", exist_ok=True)
    csv_path = f"data/scrobbles/{username}_scrobbles.csv"
    since = datetime(1970, 1, 1, tzinfo=jst)

    if update:
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reversed(list(reader)):
                    since = datetime.fromtimestamp(int(row[1]) + 1, tz=jst)
                    break

    scrobbles = await fetch_all_scrobbles(username, since)

    if os.path.exists(csv_path) and update:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for scr in reversed(scrobbles):
                writer.writerow(
                    [datetime.fromtimestamp(scr.time).strftime("%Y-%m-%d %H:%M")]
                    + [str(scr[3])]
                    + list(scr[0:3])
                )

    else:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for scr in reversed(scrobbles):
                writer.writerow(
                    [datetime.fromtimestamp(scr.time).strftime("%Y-%m-%d %H:%M")]
                    + [str(scr[3])]
                    + list(scr[0:3])
                )
