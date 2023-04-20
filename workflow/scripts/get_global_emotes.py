import os
import argparse
import asyncio
import dotenv  # type: ignore
from twitchAPI.twitch import Twitch  # type: ignore

from helpers import get_twitch_emotes, get_bttv_global_emotes


async def main():
    ap = argparse.ArgumentParser("Download global emotes from bttv and twitch.")
    ap.add_argument(
        "-i",
        "--id",
        required=True,
        help="Twitch identication as .env file with TWITCH_CLIENT_ID & TWITCH_CLIENT_SECRET",
    )
    ap.add_argument("-o", "--output", default="output", help="Output directory.")

    args = ap.parse_args()

    # Make output dirs.
    bttv_emotes_dir = os.path.join(args.output, "bttv")
    twitch_emotes_dir = os.path.join(args.output, "twitch")
    os.makedirs(bttv_emotes_dir, exist_ok=True)
    os.makedirs(twitch_emotes_dir, exist_ok=True)

    # Load app credentials.
    cred = dotenv.dotenv_values(dotenv_path=args.id)
    twitch = await Twitch(cred["TWITCH_CLIENT_ID"], cred["TWITCH_CLIENT_SECRET"])

    global_emotes = await twitch.get_global_emotes()
    async with asyncio.TaskGroup() as tg:
        tg.create_task(get_twitch_emotes(global_emotes, twitch_emotes_dir))
        tg.create_task(get_bttv_global_emotes(bttv_emotes_dir))


if __name__ == "__main__":
    asyncio.run(main())
