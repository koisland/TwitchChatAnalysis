import os

TWITCH_CFG = config["twitch"]
OUTPUT_DIR = config["paths"]["output_dir"]
EMOTES_DIR = TWITCH_CFG["paths"]["emote_dir"]
VOD_CHATS_DIR = TWITCH_CFG["paths"]["vod_chat_dir"]
VOD_INFO_BY_ID_FILE = "available_videos_by_id.json"


rule data_all:
    input:
        # Channel emotes dirs.
        bttv_emotes=expand(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "bttv"),
            channel=TWITCH_CFG["channel"],
        ),
        channel_emotes=expand(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "twitch"),
            channel=TWITCH_CFG["channel"],
        ),
        # Global emotes dirs.
        global_bttv_emotes=os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "bttv"),
        global_twitch_emotes=os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "twitch"),
        # Vod chat dir.
        vod_chats=expand(
            os.path.join(OUTPUT_DIR, "{channel}", VOD_CHATS_DIR),
            channel=TWITCH_CFG["channel"],
        ),
        # Vod chat info file.
        available_vods_by_id=expand(
            os.path.join(OUTPUT_DIR, "{channel}", VOD_INFO_BY_ID_FILE),
            channel=TWITCH_CFG["channel"],
        ),


rule get_channel_info:
    input:
        twitch_cred=TWITCH_CFG["paths"]["twitch_cred_file"],
    output:
        bttv_emote_dir=directory(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "bttv")
        ),
        channel_emote_dir=directory(
            os.path.join(OUTPUT_DIR, "{channel}", EMOTES_DIR, "twitch")
        ),
        vod_info=temp(os.path.join(OUTPUT_DIR, "{channel}", "available_videos.json")),
    conda:
        "../envs/twitch.yaml"
    params:
        # The emote subdirs for bttv and channel are hard-coded.
        emote_dir=lambda _, output: os.path.split(output.channel_emote_dir)[0],
        output_dir=lambda _, output: os.path.split(output.vod_info)[0],
    log:
        "logs/twitch/get_{channel}_info.log",
    benchmark:
        "benchmarks/twitch/get_{channel}_info.tsv"
    shell:
        """
        python workflow/scripts/get_channel_info.py \
        -i {input.twitch_cred} \
        -o {params.output_dir} \
        -e {params.emote_dir} \
        -c {wildcards.channel} &> {log}
        """


rule get_global_emotes:
    input:
        twitch_cred=TWITCH_CFG["paths"]["twitch_cred_file"],
    output:
        # Folder `all` for all channels given.
        bttv_emote_dir=directory(os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "bttv")),
        twitch_emote_dir=directory(
            os.path.join(OUTPUT_DIR, "all", EMOTES_DIR, "twitch")
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


rule group_vod_info_by_id:
    input:
        vod_info=rules.get_channel_info.output.vod_info,
    output:
        vod_info_by_id=os.path.join(OUTPUT_DIR, "{channel}", VOD_INFO_BY_ID_FILE),
    conda:
        "../envs/twitch.yaml"
    log:
        "logs/twitch/group_{channel}_vod_info_by_id.log",
    shell:
        """
        python workflow/scripts/group_vod_info_by_id.py -i {input} -o {output} &> {log}
        """


checkpoint get_vod_chat:
    input:
        vod_info=rules.group_vod_info_by_id.output.vod_info_by_id,
    output:
        # We do not know the ids of vods so only a directory is created.
        vod_chat_dir=directory(os.path.join(OUTPUT_DIR, "{channel}", VOD_CHATS_DIR)),
    threads: workflow.cores
    conda:
        "../envs/twitch.yaml"
    params:
        vod_type=TWITCH_CFG["type"],
        chat_fmt=TWITCH_CFG["format"],
    log:
        "logs/twitch/get_{channel}_vod_chat.log",
    benchmark:
        "benchmarks/twitch/get_{channel}_vod_chat.tsv"
    shell:
        """
        python workflow/scripts/get_vod_chat.py \
        -i {input.vod_info} \
        -o {output.vod_chat_dir} \
        -t {params.vod_type} \
        -f {params.chat_fmt} \
        -p {threads} &> {log}
        """
