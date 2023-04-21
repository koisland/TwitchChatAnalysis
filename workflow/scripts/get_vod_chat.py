import os
import re
import json
import base64
import argparse
import multiprocessing as mp
from chat_downloader import ChatDownloader  # type: ignore

from typing import Dict

RGX_FMT_CHAT_MSG = re.compile(r"([\d:]+)\s\|\s\((.*?)\)\s(.*?):\s(.*)")
CHAT_MSG_FIELDS = ["timestamp", "badges", "name", "msg"]
TIMESTAMP_LEN = 8


def extract_twitch_vod_chat(url: str, output_file: str) -> int:
    if os.path.exists(output_file):
        return 0

    chat = ChatDownloader().get_chat(url=url)

    with open(output_file, "wt") as chat_file:
        # Write header.
        chat_file.write("\t".join(CHAT_MSG_FIELDS) + "\n")

        # Iterate through messages.
        for msg in chat:
            fmt_chat_msg: str = chat.format(msg)
            # Use regex to parse message.
            if msg_info := re.search(RGX_FMT_CHAT_MSG, fmt_chat_msg):
                timestamp, badges, names, msg_text = list(msg_info.groups())

                # First pad time to standardize.
                while len(timestamp) < TIMESTAMP_LEN:
                    # if str_time close to next time unit (hour, minute, etc.)
                    if (len(timestamp) + 1) % 3 == 0:
                        # Append colon.
                        timestamp = ":" + timestamp
                    else:
                        # Pad with 0's.
                        timestamp = "0" + timestamp

                # Ignore unicode characters.
                msg_text = msg_text.encode("ascii", "replace").decode(encoding="utf-8")
                chat_file.write("\t".join([timestamp, badges, names, msg_text]) + "\n")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Download Twitch chat from a JSON list of available VODs."
    )
    ap.add_argument(
        "-i",
        "--input_vid_json",
        required=True,
        help="Input JSON file listing VOD ids and their metadata. Must include type attribute.",
    )
    ap.add_argument("-o", "--output_dir", default="output", help="Output directory.")

    ap.add_argument(
        "-p",
        "--processes",
        default=4,
        type=int,
        help="Processes to spawn each command.",
    )

    args = ap.parse_args()

    with open(args.input_vid_json, "rt") as vod_file:
        # Load vod information about channel.
        vod_info: Dict[str, Dict[str, str]] = json.load(vod_file)

    # Make dirs if not exists.
    os.makedirs(args.output_dir, exist_ok=True)

    # Run download in parallel processes.
    with mp.Pool(processes=args.processes) as pool:
        pool.starmap(
            func=extract_twitch_vod_chat,
            iterable=[
                (
                    info["url"],
                    # Convert title to base64.
                    os.path.join(
                        args.output_dir,
                        f"{id}_{base64.b64encode(str(info['title']).encode()).decode()}.tsv",
                    ),
                )
                for id, info in vod_info.items()
            ],
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
