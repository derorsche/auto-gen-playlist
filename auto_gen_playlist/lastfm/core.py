import dataclasses
from collections import Counter
from datetime import datetime
from logging import getLogger

from auto_gen_playlist.lastfm.api import get_user_history
from auto_gen_playlist.lastfm.misc import bisect_left_with_descending
from auto_gen_playlist.vars import JST
from dateutil.relativedelta import relativedelta

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
    *,
    ignore_album: bool = False,
    update: bool = False,
    refetch: bool = False,
):
    """`since <= track["date"] < until`を満たす期間の再生回数の`Counter`を返します。
    データがない場合には、`None`を返します。"""
    tracks = await get_user_history(user, update, refetch)

    if tracks is None:
        return

    since_ts = since.timestamp() if since is not None else 0
    until_ts = until.timestamp() if until is not None else 2_220_000_000

    res: list[Song] = []

    since_idx = bisect_left_with_descending(
        tracks, since_ts, key=lambda x: int(x["date"]["uts"])
    )
    until_idx = bisect_left_with_descending(
        tracks, until_ts, key=lambda x: int(x["date"]["uts"])
    )

    for track in tracks[until_idx:since_idx]:
        try:
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
    user: str,
    year: int,
    month: int,
    *,
    ignore_album: bool = False,
    update: bool = False,
    refetch: bool = False,
):
    """ユーザーの`scrobbles`のデータから、指定した月の再生回数の`Counter`を返します。データがない場合には、`None`を返します。
    `update=True`を指定した場合、先にキャッシュを更新します。
    これに加えて、`refetch=True`を指定したときは、キャッシュを破棄して全データを再取得します。"""
    return await get_user_track_counter(
        user,
        datetime(year, month, 1, tzinfo=JST),
        datetime(year, month, 1, tzinfo=JST) + relativedelta(months=1),
        ignore_album=ignore_album,
        update=update,
        refetch=refetch,
    )
