import os
import json
import base64
import argparse
import subprocess
import multiprocessing as mp

from enum import Enum
from dataclasses import dataclass, fields
from typing import Dict


@dataclass
class ChatMessage:
    timestamp: str
    user: str
    msg: str

    @property
    def is_command(self) -> bool:
        return self.msg.startswith("!")

    @property
    def is_mention(self) -> bool:
        return "@" in self.msg

    def as_tsv(self) -> str:
        return "\t".join([self.timestamp, self.user, self.msg])


class Subtitle(Enum):
    IRC = 0
    ASS = 1
    SRT = 2

    def into_chat_message(self, message: str) -> ChatMessage:
        match self:
            case Subtitle.ASS:
                raise NotImplementedError
            case Subtitle.SRT:
                raise NotImplementedError
            case Subtitle.IRC:
                split_message = message.split(" ", maxsplit=2)
                try:
                    timestamp, user, msg = split_message
                except ValueError:
                    # Message is only variable input with spaces. Assume no message.
                    msg = ""
                    timestamp, user = split_message
                # Strip timestamp delimiters.
                # String user angle brackets.
                timestamp = timestamp.strip("[]")
                user = user.strip("<>")

        return ChatMessage(timestamp, user, msg)


def into_subtitle_format(ext: str) -> Subtitle:
    match ext.lower().strip("."):
        case "ass":
            return Subtitle.ASS
        case "srt":
            return Subtitle.SRT
        case "irc":
            return Subtitle.IRC
        case _:
            raise ValueError("Invalid subtitle format.")


def convert_chat_to_tsv(input_file: str, output_file: str) -> int:
    subtitle_fmt = into_subtitle_format(os.path.splitext(input_file)[1])

    vod_chat_fh = open(input_file, "rt")
    vod_chat_tsv_fh = open(output_file, "wt")

    # Read chat file and output tsv chat file.
    with vod_chat_fh as vod_chat_file, vod_chat_tsv_fh as vod_chat_tsv_file:
        # Write header.
        tsv_fields = "\t".join(field.name for field in fields(ChatMessage))
        vod_chat_tsv_file.write(f"{tsv_fields}\n")

        match subtitle_fmt:
            case Subtitle.ASS:
                raise NotImplementedError
            case Subtitle.IRC:
                chat_messages = vod_chat_file.readlines()
            case Subtitle.SRT:
                raise NotImplementedError

        # Iterate through messages once.
        for msg in chat_messages:
            msg = msg.strip()
            chat_msg = subtitle_fmt.into_chat_message(msg)
            msg_row = chat_msg.as_tsv()
            vod_chat_tsv_file.write(f"{msg_row}\n")

    return 0


def extract_twitch_vod_chat(
    video_id: str, output_dir: str, filename: str, format: str
) -> int:
    # tcd required to download vod chats.
    # Flag no-progress does not work as self.progressbar is not initialized.
    # https://github.com/TheDrHax/Twitch-Chat-Downloader/blob/master/tcd/twitch.py#L199
    # So we toss the output.
    vod_chat_file = os.path.join(output_dir, f"v{video_id}.{format}")

    if os.path.exists(vod_chat_file) is False:
        cmd = ["tcd", "-v", video_id, "-t", output_dir, "-f", format]
        subprocess.run(
            cmd,
            shell=False,
            stderr=subprocess.DEVNULL,
        )

    # Check vod chat file path.
    assert os.path.exists(
        vod_chat_file
    ), f"VOD chat file ({vod_chat_file}) doesn't exist."

    # Create TSV output file path.
    vod_chat_tsv_file = os.path.join(output_dir, filename)

    return convert_chat_to_tsv(vod_chat_file, vod_chat_tsv_file)


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

    # https://dev.twitch.tv/docs/irc/tags/
    ap.add_argument("-f", "--format", default="irc", help="Chat format.")
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

    # Run download in parallel processes.
    with mp.Pool(processes=args.processes) as pool:
        pool.starmap(
            func=extract_twitch_vod_chat,
            iterable=[
                (
                    id,
                    args.output_dir,
                    # Convert title to base64.
                    f"{base64.b64encode(str(info['title']).encode()).decode()}.tsv",
                    args.format,
                )
                for id, info in vod_info.items()
            ],
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
