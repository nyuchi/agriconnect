#!/usr/bin/env python3
"""Load Natural Regions GeoJSON into agriculture.naturalRegions.

DRY-RUN IS THE DEFAULT. A dry run reads the files, verifies them and prints what
would be written; it never connects to a database. Writing needs --apply AND
--approved-by "<name of the owner who said yes>", and a clean verification.

    # verify only (safe anywhere)
    python scripts/load_natural_regions.py --geojson natural-regions.geojson \
        --country zimbabwe-boundary.geojson

    # write (owner-gated; the URI is read from the environment, never from argv)
    AGRICONNECT_MONGO_URI=... python scripts/load_natural_regions.py \
        --geojson natural-regions.geojson --country zimbabwe-boundary.geojson \
        --apply --approved-by "Bryan Fawcett"

The load is idempotent: each feature has a deterministic _id and is replaced in
place, so re-running changes nothing. It writes only the `naturalRegions`
collection of the `agriculture` database, and a 2dsphere index on `geometry`.
Nothing is deleted. Needs the `geo` extra (shapely, pymongo).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agriconnect import regions

DATABASE = "agriculture"
COLLECTION = "naturalRegions"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--geojson", required=True, type=Path)
    ap.add_argument("--country", type=Path, help="Zimbabwe boundary GeoJSON, for the coverage check")
    ap.add_argument("--apply", action="store_true", help="write to MongoDB (default: dry run)")
    ap.add_argument("--approved-by", help="the owner's name; required with --apply")
    args = ap.parse_args(argv)

    fc = json.loads(args.geojson.read_text())
    country = json.loads(args.country.read_text()) if args.country else None
    report = regions.verify(fc, country)
    docs = regions.stamp(fc.get("features", []))

    print(json.dumps({"verify": report, "would_write": [d["_id"] for d in docs]}, indent=2))
    if not report["ok"]:
        print("REFUSED: verification found problems; nothing written.", file=sys.stderr)
        return 2
    if country is None:
        print("REFUSED: coverage of the country boundary was not checked (--country).", file=sys.stderr)
        return 2
    if not args.apply:
        print(f"DRY RUN: {len(docs)} documents would be upserted into {DATABASE}.{COLLECTION}.")
        return 0
    if not args.approved_by:
        print("REFUSED: --apply needs --approved-by with the owner's name.", file=sys.stderr)
        return 2
    uri = os.environ.get("AGRICONNECT_MONGO_URI")
    if not uri:
        print("REFUSED: AGRICONNECT_MONGO_URI is not set.", file=sys.stderr)
        return 2

    from pymongo import GEOSPHERE, MongoClient, ReplaceOne

    col = MongoClient(uri, serverSelectionTimeoutMS=10000)[DATABASE][COLLECTION]
    col.create_index([("geometry", GEOSPHERE)], name="geometry_2dsphere")
    col.create_index([("properties.classification", 1), ("properties.vintage", 1), ("properties.code", 1)],
                     name="classification_vintage_code", unique=True)
    res = col.bulk_write([ReplaceOne({"_id": d["_id"]}, {**d, "approvedBy": args.approved_by}, upsert=True) for d in docs])
    print(f"APPLIED: upserted {res.upserted_count}, modified {res.modified_count}, matched {res.matched_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
