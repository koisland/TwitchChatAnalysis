import os
import json
import argparse
import asyncio
import aiofiles
import dotenv  # type: ignore
from twitchAPI.twitch import Twitch, GetEmotesResponse, TwitchUser  # type: ignore

from helpers import get_valid_filename, get_url_content, get_bttv_emotes

EMOTE_DIR = "emotes"
VOD_INFO_FILE = "available_videos.json"


async def get_twitch_channel_emotes(
    emote_resp: GetEmotesResponse, output_dir: str
) -> None:
    """
    Save channel emote names and images for plotting and matching later.
    """
    for emote_metadata in emote_resp.to_dict()["data"]:
        # Extra emote metadata
        # Convert emote name to filesafe name.
        emote_name = get_valid_filename(emote_metadata["name"])
        emote_url = emote_metadata["images"]["url_4x"]
        output_file = os.path.join(output_dir, f"{emote_name}.png")

        if not os.path.exists(output_file):
            await get_url_content(emote_url, output_file)


async def get_bttv_channel_emotes(twitch_user_id: str, output_dir: str) -> None:
    twitch_bttv_url = (
        f"https://api.betterttv.net/3/cached/users/twitch/{twitch_user_id}"
    )
    json_resp = await get_url_content(twitch_bttv_url)

    if json_resp:
        await get_bttv_emotes(json_resp["channelEmotes"], output_dir)


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
    ap.add_argument("-c", "--channel", nargs="+", help="Channel names.")

    args = ap.parse_args()

    # Load app credentials.
    cred = dotenv.dotenv_values(dotenv_path=args.id)
    twitch = await Twitch(cred["TWITCH_CLIENT_ID"], cred["TWITCH_CLIENT_SECRET"])

    # Iterate through users to get info.
    async for user in twitch.get_users(logins=args.channel):
        emote_dir = os.path.join(args.output, EMOTE_DIR)
        twitch_emote_dir = os.path.join(emote_dir, "twitch")
        bttv_emote_dir = os.path.join(emote_dir, "bttv")

        # Make output dir for each user.
        os.makedirs(twitch_emote_dir, exist_ok=True)
        os.makedirs(bttv_emote_dir, exist_ok=True)

        # Get channel emotes response
        channel_emotes = await twitch.get_channel_emotes(user.id)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(get_twitch_channel_emotes(channel_emotes, twitch_emote_dir))
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
