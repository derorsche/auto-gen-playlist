from collections.abc import Callable
from functools import wraps
from logging import getLogger
from time import sleep
from typing import Any, ParamSpec, TypeVar
from urllib.parse import urlencode

from spotipy import Spotify, SpotifyException

T = TypeVar("T")
P = ParamSpec("P")

logger = getLogger(__name__)


def automatic_retry(func: Callable[P, T]) -> Callable[P, T | None]:
    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs):
        for _ in range(5):
            try:
                return func(*args, **kwargs)
            except SpotifyException as err:
                logger.error(f"{func.__name__}({args=}, {kwargs=}) failed: {err}")
                sleep(1.5)
        logger.error(
            f"{func.__name__}({args=}, {kwargs=}) failed for 5 times. Process skipped."
        )

    return inner


@automatic_retry
def search_track(
    client: Spotify,
    *,
    query: str = "",
    album: str = "",
    artist: str = "",
    track: str = "",
    year: str = "",
    genre: str = "",
) -> list[dict[str, Any]] | None:
    if not (query or album or artist or track or year or genre):
        logger.error("search_track() failed: No search query specified.")
        return

    load = {}
    if album:
        load["album"] = album
    if artist:
        load["artist"] = artist
    if track:
        load["track"] = track
    if year:
        load["year"] = year
    if genre:
        load["genre"] = genre

    res: dict[str, Any] = client.search(  # type: ignore
        q=query + urlencode(load),
        limit=20,
        type="track",
        market="JP",
    )

    if "tracks" in res and "items" in res["tracks"]:
        return res["tracks"]["items"]
    else:
        logger.error(
            f"Unexpected API response in search_track({query=}, {album=}, {artist=}, {track=}, {year=}, {genre=}): {res=}"  # noqa: E501
        )
