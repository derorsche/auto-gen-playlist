from logging import NullHandler, getLogger

from .api import detect_track
from .core import (
    Features,
    generate_recommendation_from_playlist,
    reorder_playlist_by_features,
)

getLogger(__package__).addHandler(NullHandler())

__all__ = [
    "detect_track",
    "Features",
    "generate_recommendation_from_playlist",
    "reorder_playlist_by_features",
]
