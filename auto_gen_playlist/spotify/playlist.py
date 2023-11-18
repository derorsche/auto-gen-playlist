from logging import getLogger
from typing import Any, NamedTuple, ParamSpec, TypeVar

from spotipy import Spotify, SpotifyException

from .utils import AGPException, automatic_retry

T = TypeVar("T")
P = ParamSpec("P")

logger = getLogger(__name__)


class Playlist(NamedTuple):
    name: str
    uri: str


@automatic_retry
def _playlist_items(sp: Spotify, id: str, offset: int = 0) -> dict[str, Any]:
    # cf. https://developer.spotify.com/documentation/web-api/reference/#/operations/get-playlists-tracks  # noqa: E501

    try:
        return sp.playlist_items(playlist_id=id, limit=50, offset=offset)  # type: ignore # noqa: E501
    except SpotifyException as err:
        if "Invalid playlist Id" in str(err):
            raise AGPException(f"Invalid playlist id: {id=}, process skipped.")
        raise


def playlist_fetch_songs_all(sp: Spotify, id: str) -> list[str]:
    """プレイリストに含まれる`track`をすべて取得してその`uri`のリストを返します。"""

    fetched, total = 0, 1
    uris: list[str] = []

    while fetched < total:
        res = _playlist_items(sp, id, fetched)
        total: int = res["total"]  # type: ignore
        fetched: int = fetched + res["limit"]  # type: ignore

        for item in res["items"]:  # type: ignore
            if "track" in item and item["track"]["type"] == "track":
                uris.append(item["track"]["uri"])

    return uris


@automatic_retry
def _playlist_add_items(sp: Spotify, playlist_id: str, ids: list[str]):
    # cf. https://developer.spotify.com/documentation/web-api/reference/add-tracks-to-playlist  # noqa: E501

    sp.playlist_add_items(playlist_id, ids)


def playlist_add_songs_all(sp: Spotify, playlist_id: str, uris: list[str]):
    """プレイリストに`uris`によって示される`track`をすべて追加します。`id`や`url`を渡しても機能します。"""

    added = 0
    while added < len(uris):
        _playlist_add_items(sp, playlist_id, uris[added : added + 100])
        added += 100


@automatic_retry
def _playlist_remove_songs(sp: Spotify, playlist_id: str, ids: list[str]):
    # cf. https://developer.spotify.com/documentation/web-api/reference/remove-tracks-playlist  # noqa: E501

    sp.playlist_remove_all_occurrences_of_items(playlist_id, ids)


def playlist_remove_songs_all(sp: Spotify, id: str):
    """プレイリストに含まれる`track`をすべて削除します。引数は`id`ではなく`url`でも機能します。"""

    ids = playlist_fetch_songs_all(sp, id)
    removed = 0
    while removed < len(ids):
        _playlist_remove_songs(sp, id, ids[removed : removed + 100])
        removed += 100


@automatic_retry
def _user_playlist(sp: Spotify, offset: int) -> dict[str, Any]:
    return sp.current_user_playlists(limit=50, offset=offset)  # type: ignore


def user_fetch_playlists_all(sp: Spotify):
    """ユーザーのプレイリストをすべて取得して返します。"""

    fetched, total = 0, 1
    pls: list[Playlist] = []

    while fetched < total:
        res = _user_playlist(sp, fetched)
        total: int = res["total"]  # type: ignore
        fetched: int = fetched + res["limit"]  # type: ignore

        for item in res["items"]:  # type: ignore
            pls.append(Playlist(item["name"], item["uri"]))

    return pls
