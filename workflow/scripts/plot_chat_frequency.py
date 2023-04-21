import re
import os
import sys
import base64
import pprint
import argparse
import numpy as np  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.ticker as ticker  # type: ignore
import pandas as pd

from pandas.core.groupby.generic import DataFrameGroupBy
from scipy.signal import find_peaks  # type: ignore
from typing import Dict, Any, List


SUBPLOT_HEIGHT = 7.5
SUBPLOTS_PER_COL = 4


class KeyValStringParser(argparse.Action):
    # https://stackoverflow.com/a/56521375
    def __call__(self, parser, args, values, option_string=None):
        d = getattr(args, self.dest) or {}
        for pattern in values:
            try:
                (k, v) = pattern.split("=", 2)
            except ValueError:
                raise argparse.ArgumentError(
                    self, f'Could not parse argument "{pattern}" as k=v format.'
                )
            d[k] = v
        setattr(args, self.dest, d)


def pattern_counts(
    grp_df: DataFrameGroupBy,
    name: str,
    col: str,
    pattern: str,
    pattern_desc: str,
    *,
    ignorecase: bool = False,
) -> pd.DataFrame:
    params: Dict[str, Any] = {"regex": True}
    if ignorecase:
        params["flags"] = re.IGNORECASE

    return (
        grp_df[col]
        .aggregate(lambda x: x.str.contains(pattern, **params).sum())
        .reset_index()
        .rename(columns={col: "counts"})
        .assign(**{"desc": pattern_desc, "name": name})
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Plot chat message frequency alongside word patterns."
    )
    ap.add_argument(
        "-i",
        "--input",
        nargs="+",
        help="Input chat files as TSV file with timestamp, user, and message as fields.",
    )
    ap.add_argument("-op", "--output_plot", required=True, help="Output plot file.")
    ap.add_argument("-oc", "--output_csv", required=True, help="Output CSV file.")

    ap.add_argument(
        "-f",
        "--freq",
        default="min",
        type=str,
        help="Frequency of chat to plot.",
    )
    ap.add_argument(
        "-p",
        "--patterns",
        nargs="*",
        action=KeyValStringParser,
        metavar="NAME=PATTERN",
        default={},
        help="Patterns as pattern name and pattern split by '='.",
    )
    ap.add_argument(
        "--ignorecase", action="store_true", help="Ignore case when pattern matching."
    )

    args = ap.parse_args()
    pprint.pprint(args.__dict__, stream=sys.stderr)

    return plot_chat_frequency(
        args.input,
        args.output_csv,
        args.output_plot,
        args.freq,
        args.patterns,
        ignorecase=args.ignorecase,
    )


def annotate_chat_data(
    chat_file: str,
    freq: str,
    patterns: Dict[str, str],
    *,
    ignorecase: bool = False,
) -> pd.DataFrame:
    id_b64_fname, _ = os.path.splitext(os.path.basename(chat_file))
    _, b64_vod_name = id_b64_fname.split("_")

    fname = base64.b64decode(b64_vod_name).decode()

    # Skip bad lines and emit warning.
    df = pd.read_csv(chat_file, delimiter="\t", on_bad_lines="warn")

    # Get timestamps and floor them to seconds to reduce number of points.
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S").dt.floor(
        freq=freq
    )
    df_grp_timestamp = df.groupby("timestamp")

    df_message_counts = pd.DataFrame(
        (
            (grp, len(rows), "total", fname)
            for grp, rows in df_grp_timestamp.groups.items()
        ),
        columns=["timestamp", "counts", "desc", "name"],
    )

    return pd.concat(
        [
            df_message_counts,
            # TODO: Might be worth running this step in multiple processes.
            *[
                pattern_counts(
                    df_grp_timestamp,
                    fname,
                    "msg",
                    pattern,
                    pattern_name,
                    ignorecase=ignorecase,
                )
                for pattern_name, pattern in patterns.items()
            ],
        ]
    )


def tick_lbl_setter(tick_val: np.float64, df: pd.DataFrame) -> str:
    """
    Used to assign labels by converting raw tick values to a split, timestamped string value.
    """
    try:
        idx = int(tick_val)
        # Prevent getting negative index. iloc has unexpected behavior with negative values.
        ts = str(df.iloc[idx]["timestamp"]).split(" ")[1] if idx >= 0 else ""
    except (ValueError, IndexError):
        ts = ""
    return ts


def plot_chat_frequency(
    chat_files: List[str],
    output_csv: str,
    output_plot: str,
    freq: str,
    patterns: Dict[str, str],
    *,
    ignorecase: bool = False,
) -> int:
    df_message_frequency = pd.concat(
        annotate_chat_data(file, freq, patterns, ignorecase=ignorecase)
        for file in chat_files
    )

    # Set default is peak to be False.
    df_message_frequency["is_peak"] = False

    # Number of vods.
    vods = df_message_frequency["name"].unique()
    # Set required number of rows based on number of vods.
    req_n_rows = max(1, int(len(vods) / SUBPLOTS_PER_COL))
    fig_height = req_n_rows * SUBPLOT_HEIGHT

    # Aspect ratio of 2.0.
    fig = plt.figure(figsize=(fig_height * 2, fig_height))
    # Get current figure and remove axis labels.
    ax: plt.Axes = plt.gca()
    ax.set_xticks([])
    ax.set_yticks([])

    plt.title("Chat Peak Frequencies", fontsize=10 * req_n_rows, y=1.03)

    for i, vod in enumerate(vods, 1):
        # Reset index on df_vod so can correctly access rows.
        df_vod = (
            df_message_frequency.loc[df_message_frequency["name"] == vod]
            .reset_index(drop=True)
            .drop(columns=["name"])
        )
        # Add a subplot and set current to ith position.
        subplot: plt.Axes = fig.add_subplot(
            req_n_rows,
            # Set number of columns to resize if less than 4.
            4 if len(vods) > 4 else len(vods),
            i,
        )

        unique_patterns = df_vod["desc"].unique()
        # Get unique colors for each pattern.
        colors = plt.cm.jet(np.linspace(0, 1, len(unique_patterns)))

        line_plots = []
        for pattern, color in zip(unique_patterns, colors):
            # Grab rows that match pattern.
            df_pattern_cnts = df_vod.loc[df_vod["desc"] == pattern].reset_index(
                drop=True
            )

            # Set prominence threshold of peak as difference between max and value at 90th percentile of counts.
            # Tested by hand. Allowed good number of peaks without including noise.
            # https://en.wikipedia.org/wiki/Topographic_prominence
            # https://stackoverflow.com/a/52612432
            prominence_threshold = df_pattern_cnts["counts"].max() - df_pattern_cnts[
                "counts"
            ].quantile(0.9)

            # Find peaks with prominence threshold.
            peaks, _ = find_peaks(
                df_pattern_cnts["counts"], prominence=prominence_threshold
            )

            # Add peak pts for pattern.
            subplot.plot(
                peaks,
                df_pattern_cnts.loc[peaks]["counts"],
                color=color,
                marker="o",
                linestyle="None",
            )
            # Add line plot for pattern.
            (line_plot,) = subplot.plot(
                df_pattern_cnts.index, df_pattern_cnts["counts"], color=color
            )
            line_plots.append(line_plot)

            # Label coordinates removing date from timestamp.
            for x, y in zip(peaks, df_pattern_cnts.iloc[peaks]["counts"]):
                timestamp = df_vod.iloc[x]["timestamp"]

                # Set original peak to True.
                same_timestamp = df_message_frequency["timestamp"] == timestamp
                same_pattern = df_message_frequency["desc"] == pattern
                same_cnts = df_message_frequency["counts"] == y
                is_same_peak = (same_timestamp) & (same_pattern) & (same_cnts)
                df_message_frequency.loc[is_same_peak, "is_peak"] = True

                # Get time from timestamp as %H:%M:%S and annotate point.
                timestamp = str(timestamp).split(" ")[1]
                plt.annotate(
                    xy=(x, y),
                    text=timestamp,
                    color=color,
                    xytext=(0, 5),
                    textcoords="offset points",
                )

            label_formatter = ticker.FuncFormatter(
                lambda x, _: tick_lbl_setter(x, df_pattern_cnts)
            )
            subplot.xaxis.set_major_formatter(label_formatter)
            subplot.set_xticks(
                ticks=subplot.get_xticks(),
                labels=subplot.get_xticklabels(),
                rotation=50,
            )

        # Add VOD title.
        subplot.set_title(vod)
        # Add legend to outside left position of subplot.
        # We need to pass in saved line plots as we don't want to add peaks to legend.
        subplot.legend(
            line_plots,
            unique_patterns,
            loc="upper left",
            bbox_to_anchor=(1.02, 1),
        )

    # Save figure and data.
    plt.savefig(output_plot)

    df_message_frequency.to_csv(output_csv, index=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
