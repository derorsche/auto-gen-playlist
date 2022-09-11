from logging import NullHandler, getLogger

from auto_gen_playlist.spotify.api import detect_track
from auto_gen_playlist.spotify.core import (
    Features,
    generate_recommendation_playlist,
    reorder_playlist_by_features,
)

getLogger(__package__).addHandler(NullHandler())

__all__ = [
    "detect_track",
    "Features",
    "generate_recommendation_playlist",
    "reorder_playlist_by_features",
]
