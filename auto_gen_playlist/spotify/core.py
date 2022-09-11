from enum import Enum
from logging import getLogger
from typing import Any

from scipy import spatial, stats
from spotipy import Spotify

from .api import (
    fetch_audio_features_all,
    fetch_playlist_songs_all,
    playlist_add_songs_all,
    playlist_remove_items_all,
    recursively_remove_elements,
)

logger = getLogger(__name__)


class Features(Enum):
    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-several-audio-features
    ACOUSTIC = "acousticness"
    DANCEABILITY = "danceability"
    ENERGY = "energy"
    INSTRUMENTAL = "instrumentalness"
    LIVENESS = "liveness"
    LOUDNESS = "loudness"
    BPM = "tempo"
    VALENCE = "valence"


def reorder_playlist_by_features(
    sp: Spotify, playlist_id: str, feature: Features, duplicate: bool = False
):
    """指定したプレイリストの曲を`Features`の数値に従って降順で並び替えます。
    `duplicate=True`であれば、新しいプレイリストを作成します。"""
    user: Any = sp.me()
    pl: Any = sp.playlist(playlist_id)

    if not duplicate and pl["owner"]["id"] != user["id"]:  # type: ignore
        logger.error(
            f"Not authorized: specified playlist '{pl['name']}' is not owned by the user."  # noqa: E501
        )
        return

    tracks = fetch_playlist_songs_all(sp, playlist_id)
    fts = fetch_audio_features_all(sp, [track["id"] for track in tracks])
    fts.sort(key=lambda x: x[feature.value])  # type: ignore
    fts.reverse()

    if duplicate:
        new_pl: Any = sp.user_playlist_create(
            user["id"],
            f"{pl['name']} - {feature.value}",
            public=False,
            description=f"sorted by {feature.value}",
        )
        playlist_add_songs_all(sp, new_pl["id"], [ft["id"] for ft in fts])
    else:
        playlist_remove_items_all(sp, pl["id"])
        playlist_add_songs_all(sp, pl["id"], [ft["id"] for ft in fts])
        sp.user_playlist_change_details(
            user["id"], pl["id"], description=f"sorted by {feature.value}"
        )


def sort_songs_by_similarity(
    sp: Spotify, ids: list[str], idx: int, features: list[Features]
):
    """`features`に含まれる指標の標準得点をもとにして、`ids[idx]`との距離で並び替えた`ids`を返します。"""
    fts = fetch_audio_features_all(sp, ids)

    res = []
    for ft in fts:
        res.append([ft[f.value] for f in features])
    z_list = stats.zscore(res, ddof=1)  # type: ignore

    for i in range(len(fts)):
        fts[i]["metric"] = spatial.distance.euclidean(z_list[i], z_list[idx])

    fts.sort(key=lambda x: x["metric"])
    return [ft["id"] for ft in fts]


def generate_recommendation_from_playlist(
    sp: Spotify,
    playlist_id: str,
    idx: int,
    features: list[Features],
    *,
    count: int = 25,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """プレイリストに含まれる曲の中から、`idx`で指定した曲に近い曲を選んで、これをシードにレコメンドされた曲を返します。
    `strict=True`に設定した場合、より厳密に類似した曲を選ぶように指定します。
    `count`は返される曲数の最大値であり、必ずその曲数が返されることは保証されません。"""
    tracks = fetch_playlist_songs_all(sp, playlist_id, False)
    sorted_ids = sort_songs_by_similarity(sp, [t["id"] for t in tracks], idx, features)

    target_ft = sp.audio_features([tracks[idx]["id"]])[0]  # type: ignore
    if not strict:
        load = {f"target_{features[0].value}": target_ft[features[0].value]}  # type: ignore  # noqa: E501
    else:
        load = {f"target_{f.value}": target_ft[f.value] for f in features}  # type: ignore  # noqa: E501

    recoms = sp.recommendations(seed_tracks=sorted_ids[:5], limit=count, **load)
    return recursively_remove_elements(recoms["tracks"])  # type: ignore
