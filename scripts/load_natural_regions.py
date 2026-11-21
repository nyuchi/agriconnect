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
        --database <db> --collection <name> --apply --approved-by "Bryan Fawcett"

The load is idempotent: each feature has a deterministic _id and is replaced in
place, so re-running changes nothing. It writes only the collection named by
--database/--collection (no default: where Natural Regions live is an owner decision), plus a
2dsphere index on `geometry`.
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--geojson", required=True, type=Path)
    ap.add_argument("--country", type=Path, help="Zimbabwe boundary GeoJSON, for the coverage check")
    ap.add_argument("--database", help="target database; no default (see docs/adr-places-contract.md)")
    ap.add_argument("--collection", help="target collection; no default")
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
        where = f"{args.database}.{args.collection}" if args.database and args.collection else "(target not chosen)"
        print(f"DRY RUN: {len(docs)} documents would be upserted into {where}.")
        return 0
    if not args.approved_by:
        print("REFUSED: --apply needs --approved-by with the owner's name.", file=sys.stderr)
        return 2
    if not (args.database and args.collection):
        print("REFUSED: --apply needs --database and --collection (the home of Natural Regions is an "
              "owner decision, see docs/adr-places-contract.md).", file=sys.stderr)
        return 2
    uri = os.environ.get("AGRICONNECT_MONGO_URI")
    if not uri:
        print("REFUSED: AGRICONNECT_MONGO_URI is not set.", file=sys.stderr)
        return 2

    from pymongo import GEOSPHERE, MongoClient, ReplaceOne

    col = MongoClient(uri, serverSelectionTimeoutMS=10000)[args.database][args.collection]
    # Documents carry no approver: an idempotent re-run must change nothing. The approval
    # is recorded in the PR/issue and in this run's output, not in the data.
    res = col.bulk_write([ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs])
    col.create_index([("geometry", GEOSPHERE)], name="geometry_2dsphere")
    print(f"APPLIED (approved by {args.approved_by}): upserted {res.upserted_count}, "
          f"modified {res.modified_count}, matched {res.matched_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
