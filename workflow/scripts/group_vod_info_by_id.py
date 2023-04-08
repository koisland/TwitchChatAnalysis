import json
import argparse
from typing import Dict, List


def main():
    ap = argparse.ArgumentParser(description="Group Twitch VOD metadata by id.")
    ap.add_argument("-i", "--input", help="VOD info JSON file.")
    ap.add_argument("-o", "--output", help="Output VOD info JSON file.")

    args = ap.parse_args()
    with open(args.input, "rt") as vod_info_file:
        vods: List[Dict[str, str]] = json.load(vod_info_file)

    # Create dict where id to vod metadata.
    id_vods: Dict[str, Dict[str, str]] = {
        vod["id"]: {k: v for k, v in vod.items() if k != "id"} for vod in vods
    }

    # Write out id to vod metadata json.
    with open(args.output, "wt") as vod_info_by_id_file:
        json.dump(id_vods, vod_info_by_id_file)


if __name__ == "__main__":
    raise SystemExit(main())
