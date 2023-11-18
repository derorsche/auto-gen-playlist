from logging import getLogger

from spotipy import Spotify

from .ft import Features, fetch_audio_features_all, sort_by_similarity
from .playlist import (
    playlist_add_songs_all,
    playlist_fetch_songs_all,
    playlist_remove_songs_all,
)

logger = getLogger(__name__)


def playlist_sort_by_features(sp: Spotify, id: str, feature: Features):
    """指定したプレイリストの曲を`feature`の数値に従って降順で並び替えます。"""

    user = sp.me()
    uris = playlist_fetch_songs_all(sp, id)

    fts = fetch_audio_features_all(sp, uris)
    fts.sort(key=lambda x: x[feature.value])  # type: ignore
    fts.reverse()

    playlist_remove_songs_all(sp, id)
    playlist_add_songs_all(sp, id, [ft["id"] for ft in fts])

    sp.user_playlist_change_details(
        user["id"],  # type: ignore
        id,
        description="sorted by {} (range: {:.3f} - {:.3f})".format(
            feature.value, fts[0][feature.value], fts[-1][feature.value]
        ),  # noqa: E501
    )


def fetch_recommendation(
    sp: Spotify,
    uris: list[str],
    features: list[Features],
    idx: int,
    count: int,
) -> list[str]:
    """
    `uris`に含まれる曲のうち、`idx`個目の曲を含む`idx`個目の曲に類似する5曲をシードとして、取得したレコメンドの`uri`を返します。
    `features`を指定した場合には、`idx`個目の曲の当該`Feature`の値を加えて`target`として設定します。
    """
    # cf. https://developer.spotify.com/documentation/web-api/reference/get-recommendations  # noqa: E501

    fts = fetch_audio_features_all(sp, uris)

    if features:
        load = {f"target_{f.value}": fts[idx][f.value] for f in features}  # type: ignore  # noqa: E501
    else:
        load = {}

    sort_by_similarity(fts, idx, [ft for ft in Features])  # type: ignore

    res = sp.recommendations(
        seed_tracks=[ft["uri"] for ft in fts[:5]], limit=count, **load  # type: ignore
    )
    return [track["uri"] for track in res["tracks"]]  # type: ignore
