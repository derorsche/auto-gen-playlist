import dataclasses
from collections import Counter
from datetime import datetime, timedelta
from logging import getLogger

from dateutil.relativedelta import relativedelta

from auto_gen_playlist.lastfm import load_user_history
from auto_gen_playlist.variables import JST

logger = getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class Song:
    title: str
    artist: str
    album: str


async def get_user_track_counter(
    user: str,
    since: datetime | None = None,
    until: datetime | None = None,
    ignore_album: bool = False,
):
    """ユーザーの`scrobbles`のデータから、指定した期間の再生回数の`Counter`を返します。データがない場合には、`None`を返します。"""
    tracks = await load_user_history(user)

    if tracks is None:
        return

    since_ts = since.timestamp() if since is not None else 0
    until_ts = until.timestamp() if until is not None else 2_220_000_000

    res: list[Song] = []
    for track in tracks:
        try:
            if not since_ts <= int(track["date"]["uts"]) <= until_ts:
                continue
            else:
                res.append(
                    Song(
                        track["name"],
                        track["artist"]["name"],
                        track["album"]["#text"] if not ignore_album else "",
                    )
                )
        except KeyError:
            logger.error(f"Unexpected track data: {track=}")

    return Counter(res)


async def get_user_monthly_track_counter(
    user: str, year: int, month: int, ignore_album: bool = False
):
    """ユーザーの`scrobbles`のデータから、指定した月の再生回数の`Counter`を返します。データがない場合には、`None`を返します。"""
    return await get_user_track_counter(
        user,
        datetime(year, month, 1, tzinfo=JST),
        datetime(year, month, 1, tzinfo=JST)
        + relativedelta(months=1)
        - timedelta(seconds=1),
        ignore_album,
    )
