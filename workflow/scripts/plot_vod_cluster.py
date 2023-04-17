import csv
import os
import sys
import base64
import pprint
import argparse
import matplotlib.pyplot as plt  # type: ignore
import pandas as pd  # type: ignore
import seaborn as sns  # type: ignore

from collections import Counter
from typing import Set, List, Tuple, Optional, Dict
from matplotlib.axes import Axes  # type: ignore
from matplotlib.offsetbox import OffsetImage, AnnotationBbox  # type: ignore

from plot_helpers import label_b64_files

csv.field_size_limit(sys.maxsize)
sns.set_theme(style="whitegrid")


def count_words(chat_tsv: str, word_set: Set[str]) -> pd.DataFrame:
    """
    Count words from given word set.
    """
    with open(chat_tsv, "rt") as chat_file:
        vod_name = os.path.splitext(os.path.basename(chat_tsv))[0]
        # Try to decode the vodname. Otherwise, use the original name.
        try:
            vod_name = base64.b64decode(vod_name).decode()
        except Exception:
            pass

        reader = csv.DictReader(
            chat_file,
            fieldnames=["timestamp", "user", "msg", "is_command", "is_mention"],
            delimiter="\t",
        )

        # Create counter to count words.
        word_count: Counter[int] = Counter()
        for line in reader:
            words = Counter(line["msg"].split(" "))
            # Create set of words in split message and only take words that exist in emote set.
            remove_words = set(words.keys()).difference(word_set)
            for remove_word in remove_words:
                words.pop(remove_word)
            word_count.update(words)

        return pd.DataFrame(
            {
                "file": [vod_name] * len(word_count),
                "word": word_count.keys(),
                "count": word_count.values(),
            }
        )


def add_image_annot(
    coord: Tuple[int, int], img_path: str, img_scale: float, ax: Axes
) -> None:
    """
    Add image annotation to
    Adapted from: https://stackoverflow.com/a/44264051
    """
    img = plt.imread(img_path)
    im = OffsetImage(img, zoom=img_scale)
    im.image.axes = ax

    ab = AnnotationBbox(im, xy=coord, xycoords="data", pad=0)
    ax.add_artist(ab)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Plot emote counts across VODs as clustermap."
    )
    ap.add_argument(
        "-i",
        "--input",
        nargs="+",
        help="Input chat files as TSV file with timestamp, user, and message as fields.",
    )
    ap.add_argument(
        "-e",
        "--emote_dirs",
        nargs="+",
        help="Emote directories to check in message.",
    )
    ap.add_argument("-op", "--output_plot", required=True, help="Output plot file.")
    ap.add_argument("-oc", "--output_csv", required=True, help="Output CSV file.")
    ap.add_argument(
        "-t",
        "--title",
        default="VODs Clustered by Emote",
        help="Clustermap plot title.",
    )
    ap.add_argument(
        "-m",
        "--min_emote",
        default=10,
        help="Minimum number of emotes per VOD to exclude by.",
    )
    ap.add_argument("-b", "--blacklist", nargs="*", help="Emote blacklist.")

    args = vars(ap.parse_args())
    pprint.pprint(args, stream=sys.stderr)

    return plot_vod_emotes(
        args["input"],
        args["emote_dirs"],
        args["output_csv"],
        args["output_plot"],
        plot_title=args["title"],
        min_emote_count=args["min_emote"],
        emote_blacklist=set(args["blacklist"]) if args.get("blacklist") else None,
    )


def plot_vod_emotes(
    chat_files: List[str],
    emote_dirs: List[str],
    output_csv: str,
    output_plot: str,
    *,
    min_emote_count: int = 10,
    plot_title: str = "VODs Clustered by Emote",
    emote_blacklist: Optional[Set[str]] = None,
) -> int:
    """
    Plot emote counts across VODs as hierarchically-clustered heatmap.
    """
    # Init default empty set.
    if emote_blacklist is None:
        emote_blacklist = set()

    # Create emote set and name to filename match.
    emote_to_file: Dict[str, str] = {}
    for emote_dir in emote_dirs:
        labeled_b64_files = label_b64_files(
            emote_dir, ignore_fnames=emote_blacklist, ignore_ext=(".png", ".gif")
        )
        emote_to_file = emote_to_file | labeled_b64_files

    emote_set = set(emote_to_file.keys())

    df_emote_counts = (
        pd.concat(count_words(file, emote_set) for file in chat_files)
        # Take only emotes where at least one vod has a count greater than min_emote_count.
        .query(f"count > {min_emote_count}")
        # Pivot table from tidy data to wide data.
        .pivot(index=["word"], columns=["file"], values=["count"])
        # Fill empty emote counts to 0.
        .fillna(0)
    )

    # Create cluster map where emotes on rows, files in columns.
    cmap = sns.clustermap(
        df_emote_counts,
        # No clustering emotes.
        row_cluster=False,
        figsize=(
            # Scale figure based on number of emotes and vods.
            len(df_emote_counts.columns) * 2,
            len(df_emote_counts.index) / 2,
        ),
        # Standardize count values by row (emote count across VODs).
        # https://seaborn.pydata.org/generated/seaborn.clustermap.html
        # Why? https://stats.stackexchange.com/a/192231
        standard_scale=0,
        dendrogram_ratio=0.02,
        # Distance metric is euclidean by clustermap's default.
        # Use ward as cluster linkage method.
        # https://www.statisticshowto.com/wards-method/
        method="ward",
        # Set position of cluster (x, y, width, height) to be left side.
        cbar_pos=(-0.15, 0.5, 0.05, 0.18),
        cbar_kws={
            "shrink": 0.40,
            "aspect": 40,
            "label": "Normalized Emote Counts (Across VODs)",
        },
    )
    # Add title to heatmap.
    cmap.fig.suptitle(plot_title, fontsize="xx-large", fontweight="bold", y=1.01)

    # Rename xlabels to remove multi-index label prefix, "count-"
    new_labels = []
    for lbl in cmap.ax_heatmap.axes.get_xticklabels():
        emote_lbl = lbl.get_text().replace("count-", "")
        new_labels.append(emote_lbl)
    # Rotate xlabel names by 30 degrees.
    cmap.ax_heatmap.axes.set_xticklabels(new_labels, rotation=30, ha="right")

    # Add emote icons to left side of heatmap.
    for lbl in cmap.ax_heatmap.axes.get_yticklabels():
        emote_path = emote_to_file[lbl.get_text()]
        _, lbl_y = lbl.get_position()
        add_image_annot(
            coord=(0, lbl_y),
            img_path=emote_path,
            img_scale=0.2,
            ax=cmap.ax_heatmap.axes,
        )

    # Rename axis labels.
    cmap.ax_heatmap.axes.set(xlabel="VOD", ylabel="Emote")

    # Save figure and and counts.
    df_emote_counts.to_csv(output_csv)
    cmap.savefig(output_plot)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
