from logging import getLogger
from typing import Any, ParamSpec, TypeVar

from spotipy import Spotify, SpotifyException

from .utils import automatic_retry

T = TypeVar("T")
P = ParamSpec("P")

logger = getLogger(__name__)


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
def playlist_items(
    sp: Spotify, id: str, limit: int = 100, offset: int = 0
) -> dict[str, Any] | None:
    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-playlists-tracks
    try:
        return sp.playlist_items(playlist_id=id, limit=limit, offset=offset)
    except SpotifyException as err:
        if "Invalid playlist Id" in str(err):
            logger.error(f"Invalid playlist id: {id=}, process skipped.")
            return


def fetch_playlist_songs_all(
    sp: Spotify, id: str, only_track: bool = True
) -> list[dict[str, Any]]:
    """プレイリストに含まれる曲をすべて取得して返します。デフォルトでは、`Episodes`と`Shows`を除外します。
    取得に失敗した場合には、空リストを返します。"""
    if res := playlist_items(sp, id, limit=100, offset=0):
        total: int = res["total"]
        fetched = 100
        songs: list[dict[str, Any]] = recursively_remove_elements(
            [
                item["track"]
                for item in res["items"]
                if not only_track or item["track"]["track"]
            ]
        )

        while fetched < total:
            if res_add := playlist_items(sp, id, limit=100, offset=fetched):
                songs.extend(
                    recursively_remove_elements(
                        [
                            item["track"]
                            for item in res_add["items"]
                            if not only_track or item["track"]["track"]
                        ]
                    )
                )

            fetched += 100

        return songs

    else:
        return []


@automatic_retry
def audio_features(sp: Spotify, ids: list[str]) -> list[dict[str, Any] | None]:
    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-several-audio-features
    return sp.audio_features(ids)  # type: ignore


def fetch_audio_features_all(sp: Spotify, ids: list[str]) -> list[dict[str, Any]]:
    """渡したトラックの`audio features`をすべて取得して返します。渡される`id`は全て有効なものである必要があります。
    取得に失敗した場合は、空リストを返します。"""
    fetched = 0
    fts: list[dict[str, Any] | None] = []

    while fetched < len(ids):
        if res := audio_features(sp, ids[fetched : fetched + 100]):
            fts.extend(res)
            fetched += 100
        else:
            return []

    return [ft if ft is not None else {} for ft in fts]


@automatic_retry
def playlist_add_items(sp: Spotify, playlist_id: str, ids: list[str]):
    sp.playlist_add_items(playlist_id, ids)


def playlist_add_songs_all(sp: Spotify, playlist_id: str, ids: list[str]):
    added = 0
    while added < len(ids):
        playlist_add_items(sp, playlist_id, ids[added : added + 100])
        added += 100


@automatic_retry
def playlist_remove_all_occurrences_of_items(
    sp: Spotify, playlist_id: str, ids: list[str]
):
    sp.playlist_remove_all_occurrences_of_items(playlist_id, ids)


def playlist_remove_items_all(sp: Spotify, playlist_id: str):
    ids = [track["id"] for track in fetch_playlist_songs_all(sp, playlist_id, False)]
    removed = 0
    while removed < len(ids):
        playlist_remove_all_occurrences_of_items(
            sp, playlist_id, ids[removed : removed + 100]
        )
        removed += 100
