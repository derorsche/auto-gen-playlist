import os
from logging import getLogger
from typing import Any

from spotipy import Spotify

from auto_gen_playlist import lastfm, spotify
from auto_gen_playlist.spotify.api import (
    fetch_audio_features_all,
    playlist_add_songs_all,
)

logger = getLogger(__name__)


async def generate_bimestrial_top_track_playlist(
    sp: Spotify, year: int, index: int, count: int = 45
):
    """ユーザーの2か月間の再生回数上位曲でプレイリストを作成します。`index`には1から6の数字を指定できます。"""
    if not (1 <= index <= 6):
        logger.error(f"index must be from 1 to 6, got {index}.")
        return

    counter = await lastfm.get_user_two_months_track_counter(
        os.environ["LAST_FM_USER_NAME"],
        year,
        (index - 1) * 2 + 1,
        ignore_album=True,
        update=True,
    )

    if counter is None:
        logger.error(
            f"Failed to get counter of {os.environ['LAST_FM_USER_NAME']}, process skipped."  # noqa: E501
        )
        return
    elif len(counter) == 0:
        logger.error(
            "No listening data available in specified period ({}/{:02} - {}/{:02}), process skipped.".format(  # noqa: E501
                year, (index - 1) * 2 + 1, year, (index - 1) * 2 + 2
            )
        )
        return

    song_ids: list[str] = []
    for track, _ in counter.most_common():
        if song := spotify.detect_track(sp, track.title, track.artist):
            song_ids.append(song["id"])
        else:
            logger.info(f"Failed to find {track.artist} - {track.title}, song skipped.")
        if len(song_ids) == count:
            break

    user: Any = sp.me()
    pl: Any = sp.user_playlist_create(
        user["id"],
        f"Top Tracks {year} #{index}",
        False,
        description="created by auto_gen_playlist",
    )

    fts = fetch_audio_features_all(sp, song_ids)
    fts.sort(key=lambda x: int(x["tempo"]))
    playlist_add_songs_all(sp, pl["id"], [ft["id"] for ft in fts])
