import json
import argparse
import subprocess
import multiprocessing as mp


def extract_twitch_chat(
    video_id: str, output_dir: str, format: str
) -> subprocess.CompletedProcess[bytes]:
    # tcd required to download vod chats.
    return subprocess.run(
        ["tcd", "-v", video_id, "-t", output_dir, "-f", format], shell=False
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Download Twitch chat from a JSON list of available VODs."
    )
    ap.add_argument(
        "-i",
        "--input_vid_json",
        required=True,
        help="Input JSON file listing VODs and their metadata.",
    )
    ap.add_argument("-o", "--output_dir", default="output", help="Output directory.")
    ap.add_argument(
        "-t",
        "--type_vod",
        default="archive",
        help="VOD type.",
        choices=["archive", "highlight"],
    )
    # https://dev.twitch.tv/docs/irc/tags/
    ap.add_argument("-f", "--format", default="irc", help="Chat format.")
    ap.add_argument(
        "-p", "--processes", default=4, help="Processes to spawn each command."
    )

    args = ap.parse_args()

    with open(args.input_vid_json, "rt") as vod_file:
        # Load vod information about channel.
        vod_info = json.load(vod_file)

    # Extract vods of desired type.
    vod_info = [vod for vod in vod_info if vod["type"] == args.type_vod]

    # Run download in parallel processes.
    with mp.Pool(processes=args.processes) as pool:
        process = pool.starmap(
            func=extract_twitch_chat,
            iterable=[(vod["id"], args.output_dir, args.format) for vod in vod_info],
        )
        for res in process:
            assert res.returncode == 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
