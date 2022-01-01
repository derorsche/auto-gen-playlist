import asyncio
import bisect
import csv
import os
from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple

from dateutil.relativedelta import relativedelta

from fetch import Scrobble, update_or_fetch_scrobbles
from variant import load_scrobbles


def count_top_tracks(
    scrobbles: List[Scrobble], removal_dict: Dict[str, str]
) -> Counter:
    """
    returns a counter of (title, artist) except for songs in removal_dict.

    songs which have the same (title, artist) will be treated as identical.

    can't distinguish songs like:

    - Intro by Alt-J (An Awesome Wave) / Intro by Alt-J (This Is All Yours)

    - The 1975 by The 1975 (ABIIOR) / The 1975 by The 1975 (NOACF)

    and songs which have different (title, artist) will be treated as different.

    - インパーフェクション by ヒトリエ / インパーフェクション by Hitorie

    - Paranoid Android by Radiohead / Paranoid Android - Remastered by Radiohead
    """

    res = []

    for scr in scrobbles:
        if (scr.title, scr.artist) not in removal_dict:
            res.append((scr.title, scr.artist))

    return Counter(res)


def calculate_top_tracks(username: str) -> Tuple[datetime, List[Counter]]:
    """
    this function splits one year into six "seasons" (Jan-Feb, Mar-Apr, ..., Nov-Dec)

    and from saved scrobbles, returns a counter of (title, artist) for every seasons.

    counter will be made from the first season

    which the user has scrobbled for more than one month, to the last season passed.

    for example, if it's November 3rd, 2021 today,

    - user A (first scrobbled on 2020/Oct) -> 2020/Nov-Dec to 2021/Sep-Oct

    - user B (first scrobbled on 2020/Jan) -> 2020/Jan-Feb to 2021/Sep-Oct
    """

    scrobbles = load_scrobbles(username)
    start = datetime.fromtimestamp(scrobbles[0].time)
    end = datetime.fromtimestamp(scrobbles[-1].time)

    ref_time = datetime(end.year, (end.month - (end.month % 2) + 1) % 12, 1)
    count = (ref_time.month - start.month) // 2 + (ref_time.year - start.year) * 6

    counter_list = []

    for num in range(count, 0, -1):
        since = (ref_time - relativedelta(months=2 * num)).timestamp()
        until = (ref_time - relativedelta(months=2 * (num - 1))).timestamp() - 1

        start = bisect.bisect_left([scr.time for scr in scrobbles], since)
        end = bisect.bisect_left([scr.time for scr in scrobbles], until)

        counter = count_top_tracks(scrobbles[start:end], {})
        counter_list.append(counter)

    return (ref_time - relativedelta(months=2 * count), counter_list)


async def make_top_track_playlists(username: str) -> None:
    os.makedirs("data/others/", exist_ok=True)
    csv_path = f"data/others/{username}_top_tracks.csv"
    removal_dict = {}

    await update_or_fetch_scrobbles(username)
    since, counter_list = calculate_top_tracks(username)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for counter in counter_list:
            writer.writerow(
                [
                    "Top Tracks {}: {}-{}".format(
                        since.year,
                        since.strftime("%b"),
                        (since + relativedelta(months=1)).strftime("%b"),
                    ),
                    "",
                    "",
                    "",
                ]
            )
            index = 1
            for pair in counter.most_common():
                if pair[0] not in removal_dict:
                    writer.writerow(
                        ["{:2}".format(index), pair[0][0], pair[0][1], pair[1]]
                    )
                    removal_dict[pair[0]] = ""
                    index += 1
                if index == 31:
                    break
            writer.writerow(["", "", "", ""])
            since += relativedelta(months=2)


async def main() -> None:
    print("Enter the username of the account you want to make top track playlists.")
    username = input("username: ")
    await make_top_track_playlists(username)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
