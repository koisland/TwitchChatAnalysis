import os

TWITCH_CFG = config["twitch"]
OUTPUT_DIR = config["paths"]["output_dir"]
EMOTES_DIR = TWITCH_CFG["paths"]["emote_dir"]
VOD_CHATS_DIR = TWITCH_CFG["paths"]["vod_chat_dir"]
VOD_INFO_FILE = "available_videos.json"
VOD_INFO_BY_ID_FILE = "available_videos_by_id.json"
TOP_N = TWITCH_CFG["vod"]["top_n"]


rule data_all:
    input:
        # Channel emotes dirs.
        bttv_emotes=expand(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "bttv"),
            channel=TWITCH_CFG["channel"],
        ),
        bttv_emotes_key=expand(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "bttv", "key.json"),
            channel=TWITCH_CFG["channel"],
        ),
        channel_emotes=expand(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "twitch"),
            channel=TWITCH_CFG["channel"],
        ),
        channel_emotes_key=expand(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "twitch", "key.json"),
            channel=TWITCH_CFG["channel"],
        ),
        # Global emotes dirs.
        global_bttv_emotes=os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "bttv"),
        global_bttv_emotes_key=os.path.join(
            OUTPUT_DIR, "all", EMOTES_DIR, "bttv", "key.json"
        ),
        global_twitch_emotes=os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "twitch"),
        global_twitch_emotes_key=os.path.join(
            OUTPUT_DIR, "all", EMOTES_DIR, "twitch", "key.json"
        ),
        # Vod chat dir.
        vod_chats=expand(
            os.path.join(OUTPUT_DIR, "{channel}", VOD_CHATS_DIR),
            channel=TWITCH_CFG["channel"],
        ),
        # VOD info. Both original and filtered.
        available_vods=expand(
            os.path.join(OUTPUT_DIR, "{channel}", VOD_INFO_FILE),
            channel=TWITCH_CFG["channel"],
        ),
        available_vods_by_id_filtered=expand(
            os.path.join(OUTPUT_DIR, "{channel}", VOD_INFO_BY_ID_FILE),
            channel=TWITCH_CFG["channel"],
        ),


checkpoint get_channel_info:
    input:
        twitch_cred=TWITCH_CFG["paths"]["twitch_cred_file"],
    output:
        bttv_emote_dir=directory(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "bttv")
        ),
        channel_emote_dir=directory(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "twitch")
        ),
        bttv_emote_key=os.path.join(
            OUTPUT_DIR, "{channel}", EMOTES_DIR, "bttv", "key.json"
        ),
        channel_emote_key=os.path.join(
            OUTPUT_DIR, "{channel}", EMOTES_DIR, "twitch", "key.json"
        ),
        vod_info=os.path.join(OUTPUT_DIR, "{channel}", VOD_INFO_FILE),
    conda:
        "../envs/twitch.yaml"
    log:
        "logs/twitch/get_{channel}_info.log",
    benchmark:
        "benchmarks/twitch/get_{channel}_info.tsv"
    shell:
        """
        python workflow/scripts/get_channel_info.py \
        -i {input.twitch_cred} \
        -c {wildcards.channel} \
        --output_vod_info {output.vod_info} \
        --output_emotes_bttv {output.bttv_emote_dir} \
        --output_emotes_twitch {output.channel_emote_dir} &> {log}
        """


checkpoint get_global_emotes:
    input:
        twitch_cred=TWITCH_CFG["paths"]["twitch_cred_file"],
    output:
        # Folder `all` for all channels given.
        bttv_emote_dir=directory(os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "bttv")),
        twitch_emote_dir=directory(
            os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "twitch")
        ),
        bttv_emote_key=os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "bttv", "key.json"),
        channel_emote_key=os.path.join(
            OUTPUT_DIR, "all", EMOTES_DIR, "twitch", "key.json"
        ),
    conda:
        "../envs/twitch.yaml"
    params:
        output_dir=lambda _, output: os.path.split(output.bttv_emote_dir)[0],
    log:
        "logs/twitch/get_emotes_all.log",
    benchmark:
        "benchmarks/twitch/get_emotes_all.tsv"
    shell:
        """
        python workflow/scripts/get_global_emotes.py \
        -i {input.twitch_cred} \
        -o {params.output_dir} &> {log}
        """


rule filter_group_vod_info_by_id:
    input:
        vod_info=lambda wc: checkpoints.get_channel_info.get(**wc).output.vod_info,
    output:
        vod_info_by_id=os.path.join(OUTPUT_DIR, "{channel}", VOD_INFO_BY_ID_FILE),
    params:
        select_type=TWITCH_CFG["vod"]["type"],
        select_top_n=f"--select_top_n {TOP_N}" if TOP_N else "",
        sort_by=TWITCH_CFG["sort"]["by"],
        sort_desc="--sort_desc" if TWITCH_CFG["sort"]["desc"] else "",
    conda:
        "../envs/twitch.yaml"
    log:
        "logs/twitch/group_{channel}_vod_info_by_id.log",
    shell:
        """
        python workflow/scripts/group_vod_info_by_id.py \
        -i {input} \
        -o {output} \
        --sort_by {params.sort_by} \
        {params.sort_desc} \
        --select_type {params.select_type} \
        {params.select_top_n} &> {log}
        """


checkpoint get_vod_chat:
    input:
        vod_info=rules.filter_group_vod_info_by_id.output.vod_info_by_id,
    output:
        # We do not know the ids of vods so only a directory is created.
        vod_chat_dir=directory(os.path.join(OUTPUT_DIR, "{channel}", VOD_CHATS_DIR)),
    threads: workflow.cores
    conda:
        "../envs/twitch.yaml"
    params:
        chat_fmt=TWITCH_CFG["chat_format"],
    log:
        "logs/twitch/get_{channel}_vod_chat.log",
    benchmark:
        "benchmarks/twitch/get_{channel}_vod_chat.tsv"
    shell:
        """
        python workflow/scripts/get_vod_chat.py \
        -i {input.vod_info} \
        -o {output.vod_chat_dir} \
        -f {params.chat_fmt} \
        -p {threads} &> {log}
        """
