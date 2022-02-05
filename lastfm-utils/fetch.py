import asyncio
import os
from typing import Any, Dict

import aiohttp
from aiohttp import ClientSession

from utils import misc, tracks


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

    headers = {"user-agent": os.environ["user-agent"]}
    payload = {
        "method": "user.getinfo",
        "api_key": os.environ["api-key"],
        "format": "json",
        "user": username,
    }
    root = "http://ws.audioscrobbler.com/2.0/"

    async with session.get(root, params=payload, headers=headers) as resp:
        try:
            resp.raise_for_status()
            res = await resp.json()
            if "user" in res:
                return res["user"]  # type: ignore
            else:
                return {}

        except aiohttp.ClientResponseError as err:
            print("{}: {}".format(type(err).__name__, err))
            return {}


async def main() -> None:
    print("Enter the username of the account you want to retrieve scrobbles.")
    username = input("username: ")

    misc.set_environment_var()
    await tracks.update_or_fetch_scrobbles(username)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
