import os
import base64
import sys
import matplotlib.pyplot as plt  # type: ignore

from typing import Tuple, Optional, Dict, Iterable
from matplotlib.axes import Axes  # type: ignore
from matplotlib.offsetbox import OffsetImage, AnnotationBbox  # type: ignore


def label_b64_images(
    dir: str,
    ignore_fnames: Optional[Iterable[str]] = None,
    keep_ext: Optional[Iterable[str]] = None,
) -> Dict[str, str]:
    # Set defaults
    if ignore_fnames is None:
        ignore_fnames = []

    if keep_ext is None:
        keep_ext = [".png", ".gif"]

    fname_to_path = {}
    for full_fname in os.listdir(dir):
        full_fname_no_ext, ext = os.path.splitext(full_fname)
        # Ignore extensions.
        if ext not in keep_ext:
            continue

        # Names are base64 encode so filesafe.
        if full_fname in ignore_fnames:
            continue

        fname = os.path.basename(full_fname_no_ext)
        try:
            decoded_fname = base64.b64decode(fname).decode()
        except Exception as err:
            sys.stderr.write(f"Cannot b64decode {fname}: {err}")
            continue
        fname_to_path[decoded_fname] = os.path.join(dir, full_fname)

    return fname_to_path


def add_image_annot(
    ax: Axes, coord: Tuple[int, int], img_path: str, img_scale: float
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
