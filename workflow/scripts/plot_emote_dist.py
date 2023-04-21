import os
import argparse
import squarify  # type:ignore

# import wordcloud
import pandas as pd
import matplotlib.pyplot as plt  # type:ignore

from PIL import Image
from typing import Dict
from matplotlib.text import Text  # type:ignore
from matplotlib.offsetbox import AnnotationBbox, OffsetImage  # type:ignore

from plot_helpers import label_b64_images

# https://github.com/laserson/squarify#example
SQFY_RECT_X, SQFY_RECT_Y = 0, 0
SQFY_RECT_W, SQFY_RECT_H = 800, 400
FIG_SIZE = (16, 8)


def main() -> int:
    ap = argparse.ArgumentParser(description="Plot emote distribution for VODs.")
    ap.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input counts as multi-indexed CSV. Three header rows: [count, file, and word]",
    )
    # ap.add_argument("-oc", "--output_cloud", default="./output/cloud", help="Output directory for cloud plots.")
    ap.add_argument(
        "-ot",
        "--output_tree",
        default="./output/treemap",
        help="Output directory for treemap plots.",
    )
    ap.add_argument(
        "-e",
        "--emote_dirs",
        nargs="+",
        help="Emote directories containing emote images.",
    )
    ap.add_argument(
        "-b", "--blacklisted_emotes", nargs="*", help="Emote files to ignore."
    )
    args = ap.parse_args()

    df = (
        # Only use file row from multindex pivot table
        pd.read_csv(args.input, header=[1])
        # Drop other header rows
        .dropna()
        .rename(columns={"file": "word"})
        .set_index("word")
    )
    # Get all emote files.
    all_emote_images: Dict[str, Image.Image] = {}
    for emote_dir in args.emote_dirs:
        emote_img_paths = label_b64_images(
            emote_dir, ignore_fnames=args.blacklisted_emotes, keep_ext=(".png", ".gif")
        )
        for emote_name, emote_path in emote_img_paths.items():
            # Open file and convert to RGBA to preserve image transparency, if any.
            img = Image.open(emote_path).convert("RGBA")
            all_emote_images[emote_name] = img

    # Make output dir.
    os.makedirs(args.output_tree, exist_ok=True)

    for id_vod_name in df.columns:
        id, vod_name = id_vod_name.split("_", maxsplit=1)
        # Filter based on available emotes.
        emote_freq = df.loc[df[id_vod_name] != 0.0, id_vod_name].to_dict()

        # emotecloud_title = f"Emote Cloud ({vod_name})"
        treemap_title = f"Emote Treemap ({vod_name})"

        # emotecloud_output_file = os.path.join(args.output_cloud, f"emote_cloud_{id_vod_name}.png")
        treemap_output_file = os.path.join(args.output_tree, f"treemap_{id}.png")

        # plot_chat_emote_cloud(
        #     emote_freq=emote_freq,
        #     figsize=FIG_SIZE,
        #     title=emotecloud_title,
        #     output_file=emotecloud_output_file
        # )
        plot_chat_emote_treemap(
            emote_freq=emote_freq,
            title=treemap_title,
            emote_to_img_map=all_emote_images,
            output_file=treemap_output_file,
        )

    return 0


# def plot_chat_emote_cloud(emote_freq: Dict[str, int], figsize: Tuple[int, int], title: str, output_file: str) -> int:
#     plt.clf()

#     wordcloud.WordCloud(
#         width=figsize[0],
#         height=figsize[1]
#     ).generate_from_frequencies(emote_freq)

#     plt.title(title)
#     plt.axis("off")
#     plt.tight_layout(pad = 0)
#     plt.imsave(fname=output_file)
#     return 0


def plot_chat_emote_treemap(
    emote_freq: Dict[str, int],
    title: str,
    emote_to_img_map: Dict[str, Image.Image],
    output_file: str,
) -> int:
    # Clear plot
    plt.close()

    # Normalize sizes to width and height of rectangles in plot.
    norm_emote_cnts = squarify.normalize_sizes(
        emote_freq.values(), SQFY_RECT_W, SQFY_RECT_H
    )
    # Create emote to rect mapping.
    # Need later to adjust image size to fit rectangle.
    rects = dict(
        zip(
            emote_freq.keys(),
            squarify.squarify(
                norm_emote_cnts,
                x=SQFY_RECT_X,
                y=SQFY_RECT_Y,
                dx=SQFY_RECT_W,
                dy=SQFY_RECT_H,
            ),
        )
    )

    fig = plt.figure(figsize=FIG_SIZE)
    ax: plt.Axes = fig.add_subplot(111)

    fig = squarify.plot(
        sizes=norm_emote_cnts,
        label=emote_freq.keys(),
        ax=ax,
        bar_kwargs={"edgecolor": "black"},
    )
    plt.title(title)
    # Remove numeric axes.
    plt.axis("off")
    plt.tight_layout(pad=0)

    # Get all element in figure.
    for child in fig.get_children():
        # If text label.
        if isinstance(child, Text):
            emote_name = child.get_text()
            # If emote name is not an emote img file, skip.
            if emote_name not in emote_to_img_map.keys():
                continue

            # Get saved image.
            img = emote_to_img_map[emote_name]
            img_bbox = img.getbbox()
            # If cannot get bbox of image to rescale, skip.
            if img_bbox is None:
                continue

            # Set text to blank.
            child.set_text("")

            # Get image and rectangle dimensions
            img_dim = dict(zip(["x", "y"], img_bbox[2:]))
            rect_dim = rects[emote_name]
            rect_x_dim, rect_y_dim = rect_dim["dx"], rect_dim["dy"]
            # Find which axis of rect dims is smallest.
            min_dim = "x" if rect_x_dim == min(rect_x_dim, rect_y_dim) else "y"

            # Adjust image dimensions to fit within rectangle's smallest dim.
            img_rect_dim_ratio = img_dim[min_dim] / rect_dim["d" + min_dim]
            new_img_dim = (
                int(img_dim["x"] / img_rect_dim_ratio),
                int(img_dim["y"] / img_rect_dim_ratio),
            )

            # Resize image.
            img = img.resize(size=new_img_dim)

            # Create offset image inside figure.
            im = OffsetImage(img)
            im.image.axes = fig

            ab = AnnotationBbox(
                im, xy=child.get_position(), xycoords="data", pad=0, frameon=False
            )
            fig.add_artist(ab)

    plt.savefig(output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
