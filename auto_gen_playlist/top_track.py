import os
from datetime import datetime
from logging import getLogger
from random import randint
from typing import Any, Optional

from dateutil.relativedelta import relativedelta
from spotipy import Spotify

from . import lastfm
from .lastfm import api
from .spotify.core import fetch_recommendation
from .spotify.ft import Features, sort_by_features
from .spotify.playlist import (
    playlist_add_songs_all,
    playlist_fetch_songs_all,
    playlist_remove_songs_all,
    user_fetch_playlists_all,
)
from .spotify.search import find_track_in_spotify
from .vars import JST

logger = getLogger(__name__)

TRACK_COUNT = 45


async def fetch_two_months_top_tracks(
    sp: Spotify, year: int, month: int, update: bool = False, refetch: bool = False
):
    """ユーザーの2か月間の再生回数上位曲のうち、Spotifyにあるトラックの`uri`を`TRACK_COUNT`個まで返します。"""
    counter = await lastfm.get_user_two_months_track_counter(
        os.environ["LAST_FM_USER_NAME"],
        year,
        month,
        update=update,
        refetch=refetch,
    )

    uris: set[str] = set()
    for track, _ in counter.most_common():
        if uri := find_track_in_spotify(sp, track.title, track.artist):
            uris.add(uri)
        else:
            logger.info(f"Failed to find {track.artist} - {track.title}, song skipped.")

        if len(uris) == TRACK_COUNT:
            break

    return list(uris)


async def generate_bimestrial_top_track_playlist(
    sp: Spotify, refetch: bool, update_old: bool, since_year: Optional[int] = None
):
    """ユーザーの2か月間の再生回数上位曲ごとにプレイリストを作成します。"""

    # refetch = True のときにはまとめて最初に再取得するとともに、開始年月日を指定
    if since_year:
        await api.get_user_history(os.environ["LAST_FM_USER_NAME"], True, refetch)
        since = datetime(since_year, 1, 1, tzinfo=JST)

    else:
        history = await api.get_user_history(
            os.environ["LAST_FM_USER_NAME"], True, refetch
        )
        first = datetime.fromtimestamp(int(history[-1]["date"]["uts"]), tz=JST)
        since = datetime(
            first.year, first.month - int(first.month % 2 == 0), 1, tzinfo=JST
        )

    pls = user_fetch_playlists_all(sp)

    while since < datetime.now(tz=JST):
        name = (
            f"{since.year}{since.month:02}_Top Tracks {since.year}_#{since.month//2+1}"
        )
        description = f"created by auto_gen_playlist on {datetime.now().strftime('%Y/%m/%d %H:%M')}"  # noqa: E501

        target_pl = None
        user = sp.me()

        if not update_old:
            if name in [pl.name for pl in pls]:
                since = since + relativedelta(months=2)
                continue
        else:
            for pl in [pl for pl in pls if pl.name == name]:
                target_pl = sp.playlist(pl.uri)
                playlist_remove_songs_all(sp, target_pl["uri"])
                sp.playlist_change_details(target_pl["uri"], description=description)
                break

        if target_pl is None:
            target_pl: Any = sp.user_playlist_create(
                user["id"],
                name,
                public=False,
                description=f"created by auto_gen_playlist on {datetime.now().strftime('%Y/%m/%d %H:%M')}",  # noqa: E501
            )

        uris = await fetch_two_months_top_tracks(sp, since.year, since.month)

        if len(uris) == 0:
            logger.error(
                "No listening data available in specified period ({0}/{1:02} - {0}/{2:02}), process skipped.".format(  # noqa: E501
                    since.year, since.month, since.month + 1
                )
            )
            since = since + relativedelta(months=2)
            continue

        uris = sort_by_features(sp, uris, Features.BPM)
        num = randint(0, len(uris) - 1)
        uris = uris[num:] + uris[:num]

        user: Any = sp.me()
        playlist_add_songs_all(sp, target_pl["uri"], uris)

        since = since + relativedelta(months=2)


def generate_recommended_playlist(sp: Spotify, playlist_id: str, idx: int):
    """指定したプレイリストとその中の一曲から新たにプレイリストを作成します。"""

    seed_songs = playlist_fetch_songs_all(sp, playlist_id)
    uris = fetch_recommendation(sp, seed_songs, [], idx - 1, 25)
    num = randint(0, len(uris) - 1)
    uris = uris[num:] + uris[:num]

    seed_pl = sp.playlist(playlist_id)

    user: Any = sp.me()
    pl: Any = sp.user_playlist_create(
        user["id"],
        datetime.now().strftime("%Y%m_auto-gen-playlist_#%d%S"),
        public=False,
        description=f"seed playlist: {seed_pl['name']}, seed song: {sp.track(seed_songs[idx-1])['name']}",  # type: ignore  # noqa: E501
    )

    playlist_add_songs_all(sp, pl["id"], uris)
