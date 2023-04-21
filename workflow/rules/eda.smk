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
        emote_clustermap=expand(
            os.path.join(
                OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_emote_clustermap.png"
            ),
            channel=config["twitch"]["channel"],
        ),
        emote_clustermap_data=expand(
            os.path.join(
                OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_emote_count_data_raw.csv"
            ),
            channel=config["twitch"]["channel"],
        ),
        # emote_count_cloud_plot=expand(
        #     os.path.join(
        #         OUTPUT_DIR, "{channel}", PLOT_DIR, "emote_cloud"
        #     ),
        #     channel=config["twitch"]["channel"],
        # ),
        emote_count_treemap_plot=expand(
            os.path.join(OUTPUT_DIR, "{channel}", PLOT_DIR, "emote_treemap"),
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
        # Get patterns from config file.
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


rule plot_emote_vod_clustering:
    input:
        vod_chats=rules.plot_chat_frequency.input.chat_file,
        bttv_channel_emote_dir=lambda wc: checkpoints.get_channel_emotes.get(
            **wc
        ).output.bttv_emote_dir,
        twitch_channel_emote_dir=lambda wc: checkpoints.get_channel_emotes.get(
            **wc
        ).output.channel_emote_dir,
        bttv_global_emote_dir=lambda wc: checkpoints.get_global_emotes.get(
            **wc
        ).output.bttv_emote_dir,
        twitch_global_emote_dir=lambda wc: checkpoints.get_global_emotes.get(
            **wc
        ).output.twitch_emote_dir,
    output:
        emote_count_clustermap=os.path.join(
            OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_emote_clustermap.png"
        ),
        emote_count_csv=os.path.join(
            OUTPUT_DIR, "{channel}", PLOT_DIR, "vods_emote_count_data_raw.csv"
        ),
    params:
        plot_title=lambda wc: f'"{wc.channel} VODs Clustered by Emote"',
        min_emote_filter=10,
        emote_blacklist=lambda _, input: " ".join(
            get_emote_blacklist(
                {
                    "bttv_channel": str(input.bttv_channel_emote_dir),
                    "twitch_channel": str(input.twitch_channel_emote_dir),
                    "bttv_global": str(input.bttv_global_emote_dir),
                    "twitch_global": str(input.twitch_global_emote_dir),
                }
            )
        ),
    conda:
        "../envs/nlp.yaml"
    log:
        "logs/twitch/plot_{channel}_emote_clustering.log",
    benchmark:
        "benchmarks/twitch/plot_{channel}_emote_clustering.tsv"
    shell:
        """
        python workflow/scripts/plot_vod_cluster.py \
        -i {input.vod_chats} \
        -e {input.bttv_channel_emote_dir} \
            {input.twitch_channel_emote_dir} \
            {input.bttv_global_emote_dir} \
            {input.twitch_global_emote_dir} \
        -op {output.emote_count_clustermap} \
        -oc {output.emote_count_csv} \
        -t {params.plot_title} \
        -b {params.emote_blacklist} \
        -m {params.min_emote_filter} &> {log}
        """


rule plot_emote_dist:
    input:
        emote_count_csv=rules.plot_emote_vod_clustering.output.emote_count_csv,
        bttv_channel_emote_dir=rules.plot_emote_vod_clustering.input.bttv_channel_emote_dir,
        twitch_channel_emote_dir=rules.plot_emote_vod_clustering.input.twitch_channel_emote_dir,
        bttv_global_emote_dir=rules.plot_emote_vod_clustering.input.bttv_global_emote_dir,
        twitch_global_emote_dir=rules.plot_emote_vod_clustering.input.twitch_global_emote_dir,
    output:
        # emote_count_clouds_dir=directory(os.path.join(
        #     OUTPUT_DIR, "{channel}", PLOT_DIR, "emote_cloud"
        # )),
        emote_count_treemaps_dir=directory(
            os.path.join(OUTPUT_DIR, "{channel}", PLOT_DIR, "emote_treemap")
        ),
    params:
        emote_blacklist=rules.plot_emote_vod_clustering.params.emote_blacklist,
    conda:
        "../envs/nlp.yaml"
    log:
        "logs/twitch/plot_{channel}_emote_distribution.log",
    benchmark:
        "benchmarks/twitch/plot_{channel}_emote_distribution.tsv"
    shell:
        """
        python workflow/scripts/plot_emote_dist.py \
        -i {input.emote_count_csv} \
        -e {input.bttv_channel_emote_dir} \
            {input.twitch_channel_emote_dir} \
            {input.bttv_global_emote_dir} \
            {input.twitch_global_emote_dir} \
        -b {params.emote_blacklist} \
        -ot {output.emote_count_treemaps_dir} &> {log}
        """
