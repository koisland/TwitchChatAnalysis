import os
import glob

OUTPUT_DIR = config["paths"]["output_dir"]
EMOTES_DIR = config["twitch"]["paths"]["emote_dir"]
VOD_CHATS_DIR = config["twitch"]["paths"]["vod_chat_dir"]

EDA_CFG = config["analysis"]
PLOT_DIR = EDA_CFG["paths"]["plot_dir"]


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


rule eda_all:
    input:
        chat_frequency_plot=expand(
            os.path.join(OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_chat_frequency.png"),
            channel=config["twitch"]["channel"],
        ),
        chat_frequency_csv=expand(
            os.path.join(OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_chat_frequency.csv"),
            channel=config["twitch"]["channel"],
        ),


rule plot_chat_frequency:
    input:
        chat_file=get_vod_list,
    output:
        freq_plot=os.path.join(
            OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_chat_frequency.png"
        ),
        freq_csv=os.path.join(
            OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_chat_frequency.csv"
        ),
    conda:
        "../envs/nlp.yaml"
    params:
        patterns=get_chat_freq_pattern_list_args(),
        ignorecase="--ignorecase" if EDA_CFG["ignorecase"] else "",
        interval=EDA_CFG["interval"],
    log:
        "logs/twitch/plot_{channel}_chat_freq.log",
    benchmark:
        "benchmarks/twitch/plot_{channel}_chat_freq.tsv"
    shell:
        """
        python workflow/scripts/plot_chat_frequency.py \
        -i {input} \
        -op {output.freq_plot} \
        -oc {output.freq_csv} \
        -f {params.interval} \
        {params.ignorecase} \
        {params.patterns} &> {log}
        """


# rule plot_emote_distribution:
