import asyncio
import csv
import os
from typing import Dict, List, Tuple

from fetch import Scrobble, update_or_fetch_scrobbles


def load_scrobbles(username: str) -> List[Scrobble]:
    csv_path = f"data/scrobbles/{username}_scrobbles.csv"
    res = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            res.append(Scrobble(row[1], row[2], row[3], int(row[4])))

    return res


def make_song_dict(scrobbles: List[Scrobble]) -> Dict[str, Dict[Tuple[str], int]]:
    """
    from saved scrobbles, make a dict like {title: {(artist, album): count}}

    sample return value
    - "Tyrant":
       - ("OneRepublic", "Dreaming Out Loud"): 15
       - ("OneRepublic", "Dreaming Out Loud (Deluxe)"): 10
    """

    song_dict: Dict[str, Dict[Tuple[str], int]] = {}

    for scr in scrobbles:
        pair = (scr.artist, scr.album)

        if scr.title not in song_dict:
            song_dict[scr.title] = {pair: 1}
        elif pair not in song_dict[scr.title]:
            song_dict[scr.title][pair] = 1
        else:
            song_dict[scr.title][pair] += 1

    return song_dict


def find_variant(username: str) -> None:
    """
    from saved scrobbles, find a song linked with different pair of (artist, album)

    may be useful to correct previous scrobbles.
    """
    song_dict = make_song_dict(load_scrobbles(username))
    variant_dict = {}

    for title in song_dict.keys():
        if len(song_dict[title]) > 1:
            dupl = sorted(list(song_dict[title].keys()))
            if tuple(dupl) not in variant_dict:
                variant_dict[tuple(dupl)] = [title]
            else:
                variant_dict[tuple(dupl)].append(title)

    csv_path = f"data/others/{username}_variant.csv"
    os.makedirs("data/others/", exist_ok=True)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for dupl in variant_dict.keys():
            writer.writerow([dupl, variant_dict[dupl]])


async def main() -> None:
    print("Enter the username of the account you want to find song variants.")
    username = input("username: ")

    await update_or_fetch_scrobbles(username)
    find_variant(username)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
