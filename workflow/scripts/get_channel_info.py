import os
import json
import argparse
import asyncio
import aiofiles
import dotenv  # type: ignore
from twitchAPI.twitch import Twitch, TwitchUser  # type: ignore
from twitchAPI.helper import first  # type: ignore

DEF_VOD_INFO_FILE = "available_videos.json"


async def get_channel_vod_info(
    twitch: Twitch, user: TwitchUser, output_file: str
) -> None:
    async with aiofiles.open(output_file, mode="wt") as vod_file:
        vod_info = [
            video.to_dict() async for video in twitch.get_videos(user_id=user.id)
        ]
        vod_info_json = json.dumps(vod_info, indent=4)
        await vod_file.write(vod_info_json)


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
        "--output_vod_info",
        default=os.path.join("output", DEF_VOD_INFO_FILE),
        help="Output VOD info file.",
    )

    args = vars(ap.parse_args())

    # Load app credentials.
    cred = dotenv.dotenv_values(dotenv_path=args["id"])
    twitch = await Twitch(cred["TWITCH_CLIENT_ID"], cred["TWITCH_CLIENT_SECRET"])

    # Iterate through users to get info.
    user = await first(twitch.get_users(logins=args["channel"]))

    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            get_channel_vod_info(
                twitch,
                user,
                output_file=args["output_vod_info"],
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
