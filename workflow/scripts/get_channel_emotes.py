import os
import argparse
import asyncio
import dotenv  # type: ignore
from twitchAPI.twitch import Twitch  # type: ignore
from twitchAPI.helper import first  # type: ignore

from twitch_helpers import get_twitch_emotes, get_url_content, get_bttv_emotes


async def get_bttv_channel_emotes(twitch_user_id: str, output_dir: str) -> None:
    twitch_bttv_url = (
        f"https://api.betterttv.net/3/cached/users/twitch/{twitch_user_id}"
    )
    json_resp = await get_url_content(twitch_bttv_url)

    if json_resp:
        await get_bttv_emotes(json_resp["channelEmotes"], output_dir)
        await get_bttv_emotes(json_resp["sharedEmotes"], output_dir)


async def main():
    ap = argparse.ArgumentParser("Download twitch emotes from a channel.")
    ap.add_argument(
        "-i",
        "--id",
        required=True,
        help="Twitch identication as .env file with TWITCH_CLIENT_ID & TWITCH_CLIENT_SECRET",
    )
    ap.add_argument("-c", "--channel", required=True, help="Channel name.")
    ap.add_argument(
        "--output_emotes_bttv",
        required=False,
        help="Emotes dir for bttv emotes. Leave blank to not download.",
    )
    ap.add_argument(
        "--output_emotes_twitch",
        required=False,
        help="Emotes dir fot twitch emotes. Leave blank to not download.",
    )

    args = vars(ap.parse_args())

    # Load app credentials.
    cred = dotenv.dotenv_values(dotenv_path=args["id"])
    twitch = await Twitch(cred["TWITCH_CLIENT_ID"], cred["TWITCH_CLIENT_SECRET"])

    # Iterate through users to get info.
    user = await first(twitch.get_users(logins=args["channel"]))

    # Get channel emotes response
    channel_emotes = await twitch.get_channel_emotes(user.id)

    async with asyncio.TaskGroup() as tg:
        if bttv_emote_dir := args.get("output_emotes_bttv"):
            os.makedirs(bttv_emote_dir, exist_ok=True)
            tg.create_task(get_bttv_channel_emotes(user.id, bttv_emote_dir))

        if twitch_emote_dir := args.get("output_emotes_twitch"):
            os.makedirs(twitch_emote_dir, exist_ok=True)
            tg.create_task(get_twitch_emotes(channel_emotes, twitch_emote_dir))


if __name__ == "__main__":
    asyncio.run(main())
