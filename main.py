import asyncio
from logging import Filter, LogRecord, config

import dotenv
import spotipy
from yaml import safe_load

from auto_gen_playlist.top_track import (
    generate_bimestrial_top_track_playlist,
    generate_recommended_playlist,
)

LOG_CONF_PATH = "etc/log-conf.yaml"
SCOPE = (
    "user-library-read playlist-read-collaborative"
    " playlist-read-private playlist-modify-private playlist-modify-public"
)


class StreamHandlerFilter(Filter):
    def filter(self, record: LogRecord):
        return "auto_gen_playlist.lastfm.requests" != record.name


def load_config():
    dotenv.load_dotenv()  # type: ignore

    with open(LOG_CONF_PATH, "r", encoding="utf-8") as f:
        yml = safe_load(f)
    config.dictConfig(yml)


async def main():
    load_config()
    sp = spotipy.Spotify(auth_manager=spotipy.oauth2.SpotifyOAuth(scope=SCOPE))

    print(
        "To create a recommended playlist, enter a playlist URL.  To create a top-track playlist, press the enter key."  # noqa: E501
    )
    url = input("... ")
    print()

    if url:
        while True:
            print("Enter the index of the seed song.")
            idx = int(input("... "))
            generate_recommended_playlist(sp, url, idx)
            print()

            print("To create another recommended playlist, enter a playlist URL.")
            url = input("... ")
            print()

    else:
        print("To delete tha cache and re-fetch the scrobbles, enter 'T'.")
        if "T" == input("... "):
            refetch = True
        else:
            refetch = False
        print()

        print("To update tha previous auto-generated top-track playlists, enter 'T'.")
        if "T" == input("... "):
            update_old = True
        else:
            update_old = False
        print()

        print("To specify the starting point, enter the year.")
        if year := input("... "):
            year = int(year)
        else:
            year = None
        print()

        await generate_bimestrial_top_track_playlist(
            sp, refetch=refetch, update_old=update_old, since_year=year
        )


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
