import asyncio
import csv
import json
import os
from asyncio.locks import Semaphore
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import aiohttp
from aiohttp import ClientSession


class Scrobble(NamedTuple):
    """
    example below. time described in unix time number.
    - title: str = "Zombie"
    - artist: str = "The Cranberries"
    - album: str = "No Need To Argue (The Complete Sessions 1994-1995)"
    - time: int = 1636191690
    """

    title: str
    artist: str
    album: str
    time: int


def load_config(key: str) -> str:
    with open("lastfm-utils/config/config.json") as f:
        df = json.load(f)
        return df[key]


async def fetch_user_info(session: ClientSession, username: str) -> Dict[str, Any]:
    """
    fetch info of the specified user. return empty dict when error occurs.

    Sample Response (only contain main part of the response)
    - name: "RJ"
    - realname: "Richard Jones"
    - url: "http://www.last.fm/user/RJ"
    - country: "UK"
    - playcount: "54189"
    - playlists: "4"
    - registered: {"unixtime": "1037793040"}
    """

    headers = {"user-agent": load_config("user-agent")}
    payload = {
        "method": "user.getinfo",
        "api_key": load_config("api-key"),
        "format": "json",
        "user": username,
    }
    root = "http://ws.audioscrobbler.com/2.0/"

    async with session.get(root, params=payload, headers=headers) as resp:
        try:
            resp.raise_for_status()
            res = await resp.json()
            if "user" in res:
                return res["user"]
            else:
                return {}

        except aiohttp.ClientResponseError as err:
            print("{}: {}".format(type(err).__name__, err))
            return {}


async def fetch_recent_tracks(
    session: ClientSession,
    username: str,
    page: Optional[int] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Tuple[int, List[Scrobble]]:
    """
    wrapper of user.getRecentTracks. formats response into List[Scrobble].
    """

    headers = {"user-agent": load_config("user-agent")}
    payload = {
        "method": "user.getrecenttracks",
        "limit": 200,
        "user": username,
        "api_key": load_config("api-key"),
        "format": "json",
    }
    root = "http://ws.audioscrobbler.com/2.0/"

    if page is not None:
        payload["page"] = page
    if since is not None:
        payload["from"] = int(since.timestamp())
    if until is not None:
        payload["to"] = int(until.timestamp())

    async with session.get(root, params=payload, headers=headers) as resp:
        try:
            resp.raise_for_status()
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

        except aiohttp.ClientResponseError as err:
            print("{}: {}".format(type(err).__name__, err))
            return (0, [])

        except KeyError as err:
            print("{}: {}".format(type(err).__name__, err))
            return (0, [])


async def limited_fetch_scrobbles(
    session: ClientSession,
    semaphore: Semaphore,
    username: str,
    page: Optional[int] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> List[Scrobble]:

    async with semaphore:
        res = await fetch_recent_tracks(session, username, page, since, until)
        print(f"fetched page {page}.")
        return res[1]


async def fetch_scrobbles(
    session: ClientSession,
    username: str,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> List[Scrobble]:
    """
    fetch all scrobbles of the specified user. can specify the time range.
    """

    if until is None:
        tz_utc = timezone(timedelta(hours=0))
        until = datetime.now(tz_utc)

    res = await fetch_recent_tracks(session, username, 1, since, until)
    semaphore = Semaphore(3)

    tasks = [
        asyncio.ensure_future(
            limited_fetch_scrobbles(session, semaphore, username, page, since, until)
        )
        for page in range(2, res[0] + 1)
    ]

    scrobbles_list = await asyncio.gather(*tasks)
    for content in scrobbles_list:
        res[1].extend(content)

    return res[1]


async def update_or_fetch_scrobbles(username: str) -> None:
    """
    retrieve all scrobbles of the specified user, and saved them as csv file.

    if scrobbles were fetched before, only newer scrobbles will be fetched.
    """

    os.makedirs("data/scrobbles/", exist_ok=True)
    csv_path = f"data/scrobbles/{username}_scrobbles.csv"
    since = None

    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reversed(list(reader)):
                since = datetime.fromtimestamp(int(row[4]) + 1)
                break

    async with ClientSession() as session:
        scrobbles = await fetch_scrobbles(session, username, since)

    if os.path.exists(csv_path):
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for scr in reversed(scrobbles):
                writer.writerow(
                    [datetime.fromtimestamp(scr.time).strftime("%Y-%m-%d %H:%M")]
                    + list(scr)
                )

    else:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for scr in reversed(scrobbles):
                writer.writerow(
                    [datetime.fromtimestamp(scr.time).strftime("%Y-%m-%d %H:%M")]
                    + list(scr)
                )


async def main() -> None:
    print("Enter the username of the account you want to retrieve scrobbles.")
    username = input("username: ")

    await update_or_fetch_scrobbles(username)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
