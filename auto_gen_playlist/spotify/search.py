from logging import getLogger
from typing import Any, TypeVar

from spotipy import Spotify

from .utils import AGPException, automatic_retry

T = TypeVar("T")
logger = getLogger(__name__)


@automatic_retry
def _search_track(sp: Spotify, query: str = "") -> list[dict[str, Any]]:
    res: dict[str, Any] = sp.search(q=query, limit=20)  # type: ignore
    # cf. https://developer.spotify.com/documentation/web-api/reference/#/operations/search  # noqa: E501

    if "tracks" in res and "items" in res["tracks"]:
        return res["tracks"]["items"]
    else:
        raise AGPException(f"Unexpected API response in search_track({query=}): {res=}")


def find_track_in_spotify(sp: Spotify, title: str, artist: str) -> str | None:
    """`Spotify`から指定した曲を検索して返します。候補が複数ある場合、

    1. 各候補が含まれる広義のアルバム（シングル、コンピレーション及びアルバム）の中に、
    指定した`artist`の狭義のアルバムがあればそれに含まれる曲
    1. なければ指定した`artist`の広義のアルバムの中で最も曲数が多いものに含まれる曲
    1. いずれもなければ検索結果で最上位にきた曲

    を返します。指定した曲名とアーティスト名に完全一致する曲がない場合、`None`を返します。"""

    def select(results: list[dict[str, Any]]) -> str | None:
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
                    and track["album"]["artists"][0]["name"].casefold()
                    == artist.casefold()
                ):
                    album_idx = idx
                    break

                if (
                    track["album"]["artists"][0]["name"].casefold() == artist.casefold()
                    and track["album"]["total_tracks"] > max_total
                ):
                    max_total = track["album"]["total_tracks"]
                    suspected_ep_idx = idx

            return (
                res[album_idx]["id"]
                if album_idx is not None
                else res[suspected_ep_idx]["id"]
            )

        else:
            return None

    sp.language = "ja"
    if ja_res := _search_track(sp, query=" ".join((title, artist))):
        if id := select(ja_res):
            return id

    sp.language = "en"
    if en_res := _search_track(sp, query=" ".join((title, artist))):
        if id := select(en_res):
            return id

    return None
