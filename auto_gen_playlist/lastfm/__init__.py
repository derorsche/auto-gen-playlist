from logging import NullHandler, getLogger

from .core import get_user_two_months_track_counter

getLogger(__package__).addHandler(NullHandler())

__all__ = ["get_user_two_months_track_counter"]
