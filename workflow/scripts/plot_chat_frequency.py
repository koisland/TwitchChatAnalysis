import re
import os
import sys
import argparse
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.ticker as ticker  # type: ignore
import pandas as pd  # type: ignore
import seaborn as sns  # type: ignore
from pandas.core.groupby.generic import DataFrameGroupBy

from typing import Dict, Any

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


def pattern_frequency(
    grp_df: DataFrameGroupBy,
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
        .assign(**{"desc": pattern_desc})
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Plot chat message frequency alongside word patterns."
    )
    ap.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input chat file as TSV file with timestamp, user, and message as fields.",
    )
    ap.add_argument("-o", "--output", required=True, help="Output plot file.")
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
    sys.stderr.write(f"Args: {args}\n")

    return plot_chat_frequency(
        args.input, args.output, args.freq, args.patterns, ignorecase=args.ignorecase
    )


def plot_chat_frequency(
    chat_file: str,
    output_file: str,
    freq: str,
    patterns: Dict[str, str],
    *,
    ignorecase: bool = False,
) -> int:
    fname, _ = os.path.splitext(os.path.basename(chat_file))
    df = pd.read_csv(chat_file, delimiter="\t")

    # Get timestamps and floor them to seconds to reduce number of points.
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S,%f").dt.floor(
        freq=freq
    )
    df_grp_timestamp = df.groupby("timestamp")

    df_message_frequency = pd.DataFrame(
        ((grp, len(rows), "total") for grp, rows in df_grp_timestamp.groups.items()),
        columns=["timestamp", "counts", "desc"],
    )

    df_message_frequency = pd.concat(
        [
            df_message_frequency,
            # TODO: Might be worth running this step in multiple processes.
            *[
                pattern_frequency(
                    df_grp_timestamp,
                    "msg",
                    pattern,
                    pattern_name,
                    ignorecase=ignorecase,
                )
                for pattern_name, pattern in patterns.items()
            ],
        ]
    )

    sns.relplot(
        data=df_message_frequency,
        kind="line",
        x="timestamp",
        y="counts",
        hue="desc",
        height=8.0,
        aspect=3.0,
    )
    # https://stackoverflow.com/questions/45289482/how-to-plot-int-to-datetime-on-x-axis-using-seaborn
    ax = plt.gca()
    ax.set_title(f"Chat Frequency ({fname})")
    label_formatter = ticker.FuncFormatter(
        lambda x, _: pd.to_datetime(x, unit="d").strftime("%H:%M:%S")
    )
    ax.xaxis.set_major_formatter(label_formatter)
    plt.xticks(rotation=50)
    plt.savefig(output_file)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
