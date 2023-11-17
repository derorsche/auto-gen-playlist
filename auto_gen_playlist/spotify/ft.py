from enum import Enum
from logging import getLogger
from typing import Any

from scipy import spatial, stats
from spotipy import Spotify

from .utils import automatic_retry

logger = getLogger(__name__)


class Features(Enum):
    # cf. https://developer.spotify.com/documentation/web-api/reference/#/operations/get-several-audio-features  # noqa: E501

    ACOUSTIC = "acousticness"
    DANCEABILITY = "danceability"
    ENERGY = "energy"
    INSTRUMENTAL = "instrumentalness"
    LIVENESS = "liveness"
    LOUDNESS = "loudness"
    BPM = "tempo"
    VALENCE = "valence"


@automatic_retry
def audio_features(sp: Spotify, ids: list[str]) -> list[dict[str, Any] | None]:
    # cf. https://developer.spotify.com/documentation/web-api/reference/#/operations/get-several-audio-features  # noqa: E501

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


def sort_by_features(sp: Spotify, uris: list[str], feature: Features) -> list[str]:
    """`uris`によって示される`track`を`feature`をもとにして降順で並び替えます。"""

    fts = fetch_audio_features_all(sp, uris)
    fts.sort(key=lambda x: x[feature.value])  # type: ignore
    fts.reverse()

    return [ft["uri"] for ft in fts]


def sort_by_similarity(
    result: list[dict[str, Any]], idx: int, features: list[Features]
):
    """トラックの`audio_features`を、`key`に含まれる指標の標準得点をもとにして、
    `idx`個目のトラックとのユークリッド距離が近い順に並び替えます。"""

    res = []
    for track in result:
        res.append([track[f.value] for f in features])
    z_list = stats.zscore(res, ddof=1)  # type: ignore

    for i in range(len(res)):
        result[i]["metric"] = spatial.distance.euclidean(z_list[i], z_list[idx])

    result.sort(key=lambda x: x["metric"])
    return result
