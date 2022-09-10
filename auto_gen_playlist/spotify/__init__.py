from logging import NullHandler, getLogger

from auto_gen_playlist.spotify.api import detect_track

getLogger(__package__).addHandler(NullHandler())

__all__ = ["detect_track"]
