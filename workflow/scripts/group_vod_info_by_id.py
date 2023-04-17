import json
import argparse
from typing import Dict, List


def main():
    ap = argparse.ArgumentParser(
        description="Group Twitch VOD metadata by id and filter."
    )
    ap.add_argument("-i", "--input", help="VOD info JSON file.")
    ap.add_argument("-o", "--output", help="Output VOD info JSON file.")
    # Sorting params.
    ap.add_argument(
        "--sort_by", type=str, default="publish_date", help="Variable to sort by."
    )
    ap.add_argument(
        "--sort_desc", action="store_true", help="Sort in descending order."
    )
    # Selecting params.
    ap.add_argument(
        "--select_top_n", type=int, required=False, help="Select top n VODs from list."
    )
    ap.add_argument(
        "--select_type",
        default="archive",
        help="VOD type.",
        choices=["archive", "highlight"],
    )

    args = vars(ap.parse_args())
    with open(args["input"], "rt") as vod_info_file:
        vods: List[Dict[str, str]] = json.load(vod_info_file)
        # Sort by sort_var.
        vods.sort(key=lambda x: x[args["sort_by"]], reverse=args["sort_desc"])

        # Take top n. Slice makes copy.
        if select_n := args.get("select_top_n"):
            vods = vods[0:select_n]

    # Create dict where id to vod metadata.
    id_vods: Dict[str, Dict[str, str]] = {
        vod["id"]: {k: v for k, v in vod.items() if k != "id"}
        for vod in vods
        if vod["type"] == args["select_type"]
    }

    # Write out id to vod metadata json.
    with open(args["output"], "wt") as vod_info_by_id_file:
        json.dump(id_vods, vod_info_by_id_file, indent=4)


if __name__ == "__main__":
    raise SystemExit(main())
