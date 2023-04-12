import os
import json
import argparse
import asyncio
import aiofiles
import dotenv  # type: ignore
from twitchAPI.twitch import Twitch, TwitchUser  # type: ignore

from helpers import get_twitch_emotes, get_url_content, get_bttv_emotes

VOD_INFO_FILE = "available_videos.json"


async def get_bttv_channel_emotes(twitch_user_id: str, output_dir: str) -> None:
    twitch_bttv_url = (
        f"https://api.betterttv.net/3/cached/users/twitch/{twitch_user_id}"
    )
    json_resp = await get_url_content(twitch_bttv_url)

    if json_resp:
        await get_bttv_emotes(json_resp["channelEmotes"], output_dir)
        await get_bttv_emotes(json_resp["sharedEmotes"], output_dir)


async def get_channel_vod_info(
    twitch: Twitch, user: TwitchUser, output_file: str
) -> None:
    async with aiofiles.open(output_file, mode="wt") as vod_file:
        vod_info = [
            video.to_dict() async for video in twitch.get_videos(user_id=user.id)
        ]
        vod_info_json = json.dumps(vod_info)
        await vod_file.write(vod_info_json)


async def main():
    ap = argparse.ArgumentParser("Download twitch emotes from a channel.")
    ap.add_argument(
        "-i",
        "--id",
        required=True,
        help="Twitch identication as .env file with TWITCH_CLIENT_ID & TWITCH_CLIENT_SECRET",
    )
    ap.add_argument("-o", "--output", default="output", help="Output directory.")
    ap.add_argument("-e", "--emotes", default="emotes", help="Emotes subdir of output.")
    ap.add_argument("-c", "--channel", nargs="+", help="Channel names.")

    args = ap.parse_args()

    # Load app credentials.
    cred = dotenv.dotenv_values(dotenv_path=args.id)
    twitch = await Twitch(cred["TWITCH_CLIENT_ID"], cred["TWITCH_CLIENT_SECRET"])

    # Iterate through users to get info.
    async for user in twitch.get_users(logins=args.channel):
        twitch_emote_dir = os.path.join(args.emotes, "twitch")
        bttv_emote_dir = os.path.join(args.emotes, "bttv")

        # Make output dir for each user.
        os.makedirs(twitch_emote_dir, exist_ok=True)
        os.makedirs(bttv_emote_dir, exist_ok=True)

        # Get channel emotes response
        channel_emotes = await twitch.get_channel_emotes(user.id)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(get_twitch_emotes(channel_emotes, twitch_emote_dir))
            tg.create_task(get_bttv_channel_emotes(user.id, bttv_emote_dir))
            tg.create_task(
                get_channel_vod_info(
                    twitch,
                    user,
                    output_file=os.path.join(args.output, VOD_INFO_FILE),
                )
            )


if __name__ == "__main__":
    asyncio.run(main())
