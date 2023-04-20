import os
import base64
import sys
from typing import Iterable, Dict


def label_b64_files(
    dir: str, ignore_fnames: Iterable[str], ignore_ext: Iterable[str]
) -> Dict[str, str]:
    fname_to_path = {}
    for full_fname in os.listdir(dir):
        full_fname_no_ext, ext = os.path.splitext(full_fname)
        # Ignore extensions.
        if ext not in ignore_ext:
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
