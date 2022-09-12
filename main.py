import asyncio
from logging import Filter, LogRecord, config
from random import randint, sample

import click
import dotenv
import spotipy
from yaml import safe_load

from auto_gen_playlist import spotify
from auto_gen_playlist.core import generate_bimestrial_top_track_playlist

LOG_CONF_PATH = "etc/log-conf.yaml"
SCOPE = (
    "user-library-read playlist-read-collaborative"
    " playlist-read-private playlist-modify-private playlist-modify-public"
)


class StreamHandlerFilter(Filter):
    def filter(self, record: LogRecord):
        return "auto_gen_playlist.lastfm.requests" != record.name


@click.group()
def cli():
    dotenv.load_dotenv()  # type: ignore

    with open(LOG_CONF_PATH, "r", encoding="utf-8") as f:
        yml = safe_load(f)
    config.dictConfig(yml)


@click.command(name="top-track")
def top_track():
    year = int(input("year (required): "))
    index = int(
        input("index (required, 1 <= index <= 6, 1: Jan-Feb, 2: Mar-Apr, ...): ")
    )
    if res := input("number of songs (optional, default: 45): "):
        count = int(res)
    else:
        count = 45
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(top_track_core(year, index, count))


async def top_track_core(year: int, index: int, count: int):
    sp = spotipy.Spotify(auth_manager=spotipy.oauth2.SpotifyOAuth(scope=SCOPE))
    await generate_bimestrial_top_track_playlist(sp, year, index, count)


@click.command()
def reorder():
    sp = spotipy.Spotify(auth_manager=spotipy.oauth2.SpotifyOAuth(scope=SCOPE))
    url = input("playlist url (required): ")
    if input("newly create playlist? (y/n): ") == "y":
        duplicate = True
    else:
        duplicate = False
    fts = [f for f in spotify.Features]
    print(", ".join([f"{cnt}: {e.value}" for cnt, e in enumerate(fts)]))
    feature = fts[int(input("specify the feature to reorder by (required, int): "))]
    spotify.reorder_playlist_by_features(sp, url, feature, duplicate)


@click.command()
def playlist():
    sp = spotipy.Spotify(auth_manager=spotipy.oauth2.SpotifyOAuth(scope=SCOPE))
    url = input("base playlist url (required): ")
    if res := input("seed song index (optional, 1-indexed): "):
        idx = int(res) - 1
    else:
        idx = None
    fts = [f for f in spotify.Features]
    print(", ".join([f"{cnt}: {e.value}" for cnt, e in enumerate(fts)]))
    if res := input("specify the features (optional, int, white-space separated): "):
        features = [fts[int(i)] for i in res.split()]
    else:
        features = sample(fts, randint(1, 3))

    spotify.generate_recommendation_playlist(sp, url, features, idx=idx, strict=True)


cli.add_command(top_track)
cli.add_command(reorder)
cli.add_command(playlist)

if __name__ == "__main__":
    cli()
