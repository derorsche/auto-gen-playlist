from logging import NullHandler, getLogger

getLogger(__package__).addHandler(NullHandler())
