from logging import NullHandler, getLogger

from auto_gen_playlist.lastfm.core import (
    get_user_track_counter,
    get_user_two_months_track_counter,
)

getLogger(__package__).addHandler(NullHandler())

__all__ = ["get_user_two_months_track_counter", "get_user_track_counter"]
