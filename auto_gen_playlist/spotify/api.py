from collections.abc import Callable
from functools import wraps
from logging import getLogger
from time import sleep
from typing import Any, ParamSpec, TypeVar

from spotipy import Spotify, SpotifyException

T = TypeVar("T")
P = ParamSpec("P")

logger = getLogger(__name__)


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


def recursively_remove_elements(res: T) -> T:
    """`res`に含まれる辞書から、`images`と`available_markets`をキーとする要素を削除します。"""
    if isinstance(res, dict):
        return {
            k: recursively_remove_elements(res[k])
            for k in res.keys()  # type: ignore
            if str(k) not in ("available_markets", "images")
        }
    elif isinstance(res, list):
        return [recursively_remove_elements(c) for c in res]  # type: ignore
    else:
        return res


@automatic_retry
def search_track(client: Spotify, query: str = "") -> list[dict[str, Any]] | None:
    if not query:
        logger.error("search_track() failed: No search query specified.")
        return

    res: dict[str, Any] = client.search(q=query, limit=20)  # type: ignore

    if "tracks" in res and "items" in res["tracks"]:
        return recursively_remove_elements(res["tracks"]["items"])
    else:
        logger.error(f"Unexpected API response in search_track({query=}): {res=}")


def detect_track(sp: Spotify, title: str, artist: str):
    """`Spotify`から指定した曲を検索して返します。指定した曲名とアーティスト名に完全一致する曲がない場合、`None`を返します。
    候補が複数ある場合、①各候補が含まれる広義のアルバム（シングル、コンピレーション及びアルバム）の中に、
    指定した`artist`の狭義のアルバムがあればそれに含まれる曲を、②なければ指定した`artist`の広義のアルバムの中で最も曲数が多いものに含まれる曲を、
    ③いずれもなければ検索結果で最上位にきた曲を返します。"""
    sp.language = "ja"
    if ja_res := search_track(sp, query=" ".join((title, artist))):
        if song := select_proper_track(ja_res, title, artist):
            return song

    sp.language = "en"
    if en_res := search_track(sp, query=" ".join((title, artist))):
        if song := select_proper_track(en_res, title, artist):
            return song

    return None


def select_proper_track(results: list[dict[str, Any]], title: str, artist: str):
    if res := [
        track
        for track in results
        if track["name"].casefold() == title.casefold()
        and track["artists"][0]["name"].casefold() == artist.casefold()
    ]:
        album_idx: int | None = None
        suspected_ep_idx = 0
        max_total = 0

        for idx, track in enumerate(res):
            if (
                track["album"]["album_type"] == "album"
                and track["album"]["artists"][0]["name"].casefold() == artist.casefold()
            ):
                album_idx = idx
                break

            if (
                track["album"]["album_type"] != "compilation"
                and track["album"]["artists"][0]["name"].casefold() == artist.casefold()
                and track["album"]["total_tracks"] > max_total
            ):
                max_total = track["album"]["total_tracks"]
                suspected_ep_idx = idx

        return res[album_idx] if album_idx is not None else res[suspected_ep_idx]

    else:
        return None
