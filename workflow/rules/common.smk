import os


def get_vod_list(wildcards) -> list:
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
