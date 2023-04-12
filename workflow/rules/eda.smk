import os

OUTPUT_DIR = config["paths"]["output_dir"]
EMOTES_DIR = config["twitch"]["paths"]["emote_dir"]
VOD_CHATS_DIR = config["twitch"]["paths"]["vod_chat_dir"]

EDA_CFG = config["analysis"]
PLOT_DIR = EDA_CFG["paths"]["plot_dir"]


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
