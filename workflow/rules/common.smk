import os
import fnmatch
import base64
from typing import Dict, List, Generator


def get_vod_list(wildcards) -> List[str]:
    """
    Get vod list of downloaded files by waiting on checkpoint get_vod_chat.
    """
    vod_dirs = checkpoints.get_vod_chat.get(**wildcards).output
    vods = glob_wildcards(os.path.join(str(vod_dirs), "{vod}.tsv")).vod
    return expand(
        os.path.join(OUTPUT_DIR, "{channel}", VOD_CHATS_DIR, "{vod}.tsv"),
        channel=config["twitch"]["channel"],
        vod=vods,
    )


def get_emote_blacklist(output_emote_dirs: Dict[str, str]) -> List[str]:
    blacklisted_files = []
    cfg_emotes = config["analysis"]["emotes"]
    for cfg_opt, directory in output_emote_dirs.items():
        all_emotes_w_path = {}
        for file in os.listdir(directory):
            fname, ext = os.path.splitext(file)
            if ext not in (".png", ".gif"):
                continue
            normal_fname = base64.b64decode(fname).decode()
            # Store the normal filename and the b64 encoded path.
            all_emotes_w_path[normal_fname] = os.path.join(directory, file)

        # Get a set of the full b64 encoded paths.
        all_emote_paths = set(all_emotes_w_path.values())

        if whitelist_emote_patterns := cfg_emotes[cfg_opt].get("whitelist"):
            found_files = set(
                all_emotes_w_path[found_file]
                for pattern in whitelist_emote_patterns
                for found_file in fnmatch.filter(all_emotes_w_path.keys(), pattern)
            )
            # Add all non-matching files to be blacklisted.
            blacklisted_files.extend(all_emote_paths.difference(found_files))
        elif cfg_emotes[cfg_opt].get("include_all") is False:
            blacklisted_files.extend(all_emote_paths)

    return [f'"{os.path.basename(file)}"' for file in blacklisted_files]


def get_chat_freq_pattern_list_args() -> str:
    """
    Parse pattern list from config.yaml and generate '-p' argument for plot_chat_frequency.py.
    """
    pattern_list = [
        f"{name}='{pattern}'"
        for name, pattern in EDA_CFG["frequency"]["patterns"].items()
    ]
    pattern_list_str = " ".join(pattern_list)
    return f"-p {pattern_list_str}" if pattern_list else ""
