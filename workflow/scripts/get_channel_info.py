import os
import re
import json
import argparse
import dotenv
import requests
import shutil
import asyncio
from twitchAPI.twitch import Twitch, GetEmotesResponse, TwitchUser

EMOTE_DIR = "emotes"
VOD_INFO_FILE = "available_videos.json"


def get_image(url: str, output_file: str):
    # Check for response and download file to output directory.
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(output_file, "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)


def get_valid_filename(s) -> str:
    s = str(s).strip().replace(" ", "_")
    return re.sub(r"(?u)[^-\w.]", "", s)


async def save_emotes(emote_resp: GetEmotesResponse, output_dir: str):
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
            get_image(emote_url, output_file)


async def get_channel_vod_info(twitch: Twitch, user: TwitchUser, output_file: str):
    with open(output_file, "wt") as vod_file:
        json.dump(
            [video.to_dict() async for video in twitch.get_videos(user_id=user.id)],
            vod_file,
        )


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
        user_output_dir = os.path.join(
            args.output, get_valid_filename(user.display_name)
        )
        user_output_emote_dir = os.path.join(user_output_dir, EMOTE_DIR)

        # Make output dir for each user.
        os.makedirs(user_output_emote_dir, exist_ok=True)

        # Get channel emotes response
        channel_emotes = await twitch.get_channel_emotes(user.id)
        # And save them.
        await save_emotes(channel_emotes, user_output_emote_dir)

        # Then get vod information.
        await get_channel_vod_info(
            twitch,
            user,
            output_file=os.path.join(user_output_dir, VOD_INFO_FILE),
        )


if __name__ == "__main__":
    asyncio.run(main())
