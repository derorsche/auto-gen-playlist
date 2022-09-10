from logging import NullHandler, getLogger

from auto_gen_playlist.lastfm.api import get_user_history

getLogger(__package__).addHandler(NullHandler())

__all__ = ["get_user_history"]
