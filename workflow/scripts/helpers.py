import os
import re
import sys
import json
import aiohttp  # type:ignore
import aiofiles  # type:ignore
from twitchAPI.twitch import GetEmotesResponse  # type: ignore

from typing import Any, List, Dict, Optional


async def get_url_content(url: str, output_file: Optional[str] = None) -> Any | None:
    # Check for response and download file to output directory.
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if not resp.ok:
                return None

            if output_file:
                f = await aiofiles.open(output_file, mode="wb")
                await f.write(await resp.read())
                await f.close()

                return None
            else:
                return json.loads(await resp.read())


async def get_bttv_emotes(emote_list: List[Dict[str, str]], output_dir: str) -> None:
    for emote in emote_list:
        emote_name = emote["code"]
        emote_url = f"https://cdn.betterttv.net/emote/{emote['id']}/3x"

        file_ext = "gif" if emote["animated"] else "png"
        output_file = os.path.join(output_dir, f"{emote_name}.{file_ext}")

        if not os.path.exists(output_file):
            await get_url_content(emote_url, output_file)


async def get_twitch_emotes(emote_resp: GetEmotesResponse, output_dir: str) -> None:
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
        else:
            sys.stderr.write(
                f"File, {output_file}, already exists for emote {emote_name} (Original: {emote_metadata['name']})\n"
            )


async def get_bttv_global_emotes(output_dir: str) -> None:
    global_bttv_url = "https://api.betterttv.net/3/cached/emotes/global"
    emotes = await get_url_content(global_bttv_url)
    assert type(emotes) == list, f"Received invalid type {type(emotes)} for emote list."
    return await get_bttv_emotes(emotes, output_dir=output_dir)


# https://stackoverflow.com/a/46801075
def get_valid_filename(s) -> str:
    s = str(s).strip().replace(" ", "_")
    return re.sub(r"(?u)[^-\w.]", "", s)
