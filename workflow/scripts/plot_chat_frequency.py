import re
import os
import sys
import base64
import pprint
import argparse
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.ticker as ticker  # type: ignore
import pandas as pd  # type: ignore
import seaborn as sns  # type: ignore
from pandas.core.groupby.generic import DataFrameGroupBy

from typing import Dict, Any, List

sns.set_theme(style="whitegrid")


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
    b64_fname, _ = os.path.splitext(os.path.basename(chat_file))
    fname = base64.b64decode(b64_fname).decode()

    df = pd.read_csv(chat_file, delimiter="\t")

    # Get timestamps and floor them to seconds to reduce number of points.
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S,%f").dt.floor(
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
    # Facet plot by name of stream VOD.
    g = sns.FacetGrid(
        df_message_frequency,
        col="name",
        col_wrap=2,
        height=5.0,
        aspect=2.0,
    )
    # Create lineplot with timestamp on x and message count on y.
    # Hue of line is the pattern.
    g.map_dataframe(
        sns.lineplot,
        x="timestamp",
        y="counts",
        hue="desc",
    )
    g.add_legend()

    # Set tick labels for all axes.
    for _, ax in g.axes_dict.items():
        label_formatter = ticker.FuncFormatter(
            lambda x, _: pd.to_datetime(x, unit="d").strftime("%H:%M:%S")
        )
        ax.xaxis.set_major_formatter(label_formatter)
        ax.set_xticks(ticks=ax.get_xticks(), labels=ax.get_xticklabels(), rotation=50)

    plt.savefig(output_plot)

    df_message_frequency.to_csv(output_csv, index=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
