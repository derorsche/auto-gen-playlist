from logging import getLogger
from typing import Any

from spotipy import Spotify

from .utils import automatic_retry

logger = getLogger(__name__)


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
