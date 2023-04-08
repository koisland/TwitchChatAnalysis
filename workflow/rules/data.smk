import os

TWITCH_CFG = config["twitch"]
OUTPUT_DIR = TWITCH_CFG["paths"]["output_dir"]


rule data_all:
    input:
        emotes=expand(
            os.path.join(OUTPUT_DIR, "{channel}", "emotes"),
            channel=TWITCH_CFG["channel"],
        ),
        # Only directory shown.
        vod_chats=expand(
            os.path.join(OUTPUT_DIR, "{channel}", "vod_chats"),
            channel=TWITCH_CFG["channel"],
        ),
        available_vods_by_id=expand(
            os.path.join(OUTPUT_DIR, "{channel}", "available_videos_by_id.json"),
            channel=TWITCH_CFG["channel"],
        ),


rule get_channel_info:
    input:
        twitch_cred=TWITCH_CFG["paths"]["twitch_cred_file"],
    output:
        emote_dir=directory(os.path.join(OUTPUT_DIR, "{channel}", "emotes")),
        vod_info=temp(os.path.join(OUTPUT_DIR, "{channel}", "available_videos.json")),
    conda:
        "../envs/twitch.yaml"
    params:
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
        -c {wildcards.channel} &> {log}
        """


rule group_vod_info_by_id:
    input:
        vod_info=rules.get_channel_info.output.vod_info,
    output:
        vod_info_by_id=os.path.join(
            OUTPUT_DIR, "{channel}", "available_videos_by_id.json"
        ),
    conda:
        "../envs/twitch.yaml"
    log:
        "logs/twitch/group_{channel}_vod_info_by_id.log",
    shell:
        """
        python workflow/scripts/group_vod_info_by_id.py -i {input} -o {output} &> {log}
        """


rule get_vod_chat:
    input:
        vod_info=rules.group_vod_info_by_id.output.vod_info_by_id,
    output:
        # We do not know the ids of vods so only a directory is created.
        vod_chat_dir=directory(os.path.join(OUTPUT_DIR, "{channel}", "vod_chats")),
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
