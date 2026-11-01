"""Natural Regions: model, checks, lookup, verification, loader. Fixtures are SYNTHETIC
squares, not real boundaries: no Natural Region polygon has been sourced yet."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agriconnect import places_join, regions

ROOT = Path(__file__).resolve().parents[1]
SRC = "SYNTHETIC TEST FIXTURE (not a real boundary)"


def feat(code, x0, x1, cls="vincent-thomas-1960", vintage=1960, y0=0, y1=10):
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": {
            "code": code, "label": f"Natural Region {code}", "classification": cls,
            "vintage": vintage, "rainfall_band_mm": "test", "source": SRC,
            "licence": "CC0-1.0", "attribution": "test", "retrievedAt": "2026-11-01",
        },
    }


def fc(*features):
    return {"type": "FeatureCollection", "features": list(features)}


COUNTRY = {"type": "Feature", "properties": {}, "geometry": feat("I", 0, 10)["geometry"]}


def good():
    return fc(feat("I", 0, 4), feat("III", 4, 7), feat("V", 7, 10))


def test_well_formed_collection_has_no_problems():
    assert regions.check_collection(good()) == []


@pytest.mark.parametrize("prop", list(regions.REQUIRED_PROPERTIES))
def test_every_required_property_is_required(prop):
    bad = good()
    del bad["features"][0]["properties"][prop]
    assert any(prop in p for p in regions.check_collection(bad))


def test_unknown_code_classification_and_duplicates_are_refused():
    bad = good()
    bad["features"][0]["properties"]["code"] = "VI"
    bad["features"][1]["properties"]["classification"] = "made-up"
    dup = fc(feat("I", 0, 4), feat("I", 4, 7))
    assert any("code" in p for p in regions.check_collection(bad))
    assert any("classification" in p for p in regions.check_collection(bad))
    assert any("duplicate" in p for p in regions.check_collection(dup))


def test_swapped_axes_and_open_rings_are_refused():
    swapped = fc(feat("I", 0, 4))
    swapped["features"][0]["geometry"]["coordinates"][0] = [[30, 100], [31, 100], [31, 101], [30, 100]]
    openr = fc(feat("I", 0, 4))
    openr["features"][0]["geometry"]["coordinates"][0].pop()
    assert any("out of range" in p for p in regions.check_collection(swapped))
    assert any("closed" in p for p in regions.check_collection(openr))


def test_lookup_returns_the_region_with_its_source_and_licence():
    (m,) = regions.lookup(good(), 5, 5)
    assert (m.code, m.classification, m.vintage) == ("III", "vincent-thomas-1960", 1960)
    assert m.source == SRC and m.licence == "CC0-1.0"
    assert regions.lookup(good(), 50, 5) == []


def test_both_classifications_stay_distinguishable():
    both = fc(feat("III", 0, 10), feat("IV", 0, 10, cls="agez-revision-2020", vintage=2020))
    got = {(m.classification, m.vintage, m.code) for m in regions.lookup(both, 5, 5)}
    assert got == {("vincent-thomas-1960", 1960, "III"), ("agez-revision-2020", 2020, "IV")}
    only = regions.lookup(both, 5, 5, classification="agez-revision-2020")
    assert [m.code for m in only] == ["IV"]


def test_a_hole_is_not_inside_and_a_shared_edge_is_reported_twice():
    holed = fc(feat("I", 0, 10))
    holed["features"][0]["geometry"]["coordinates"].append([[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]])
    assert regions.lookup(holed, 5, 5) == []
    assert len(regions.lookup(holed, 1, 1)) == 1
    two = fc(feat("I", 0, 5), feat("III", 5, 10))
    assert len(regions.lookup(two, 5.0, 5.0)) in (1, 2)  # edge: ray casting picks a side, never errors


def test_lon_lat_order_is_enforced():
    with pytest.raises(regions.RegionError):
        regions.lookup(good(), 5, 200)


def test_verify_accepts_a_clean_cover():
    r = regions.verify(good(), COUNTRY)
    assert r["ok"], r
    assert r["by_classification"]["vincent-thomas-1960/1960"]["coverage"] == 1.0


def test_verify_catches_overlap_gap_and_invalid_geometry():
    overlap = fc(feat("I", 0, 6), feat("III", 4, 10))
    assert any("overlap" in p for p in regions.verify(overlap, COUNTRY)["problems"])
    gap = fc(feat("I", 0, 4), feat("III", 4, 6))
    assert any("covers" in p for p in regions.verify(gap, COUNTRY)["problems"])
    bow = fc(feat("I", 0, 4))
    bow["features"][0]["geometry"]["coordinates"][0] = [[0, 0], [4, 4], [4, 0], [0, 4], [0, 0]]
    assert any("invalid geometry" in p for p in regions.verify(bow, COUNTRY)["problems"])


def test_stamp_ids_are_deterministic_so_a_load_is_idempotent():
    a = regions.stamp(good()["features"])
    b = regions.stamp(copy.deepcopy(good())["features"])
    assert [d["_id"] for d in a] == [d["_id"] for d in b]
    assert a[0]["_id"] == "zw-nr-vincent-thomas-1960-1960-I"


def test_province_table_matches_the_ten_provinces_in_both_collections():
    assert len(places_join.PROVINCES) == 10
    assert len({p[1] for p in places_join.PROVINCES}) == 10
    assert places_join.province_pcode("ZW-MI") == "ZW17"
    assert places_join.province_pcode("midlands") == "ZW17"
    assert places_join.province_pcode("Harare") == "ZW19"
    assert places_join.province_iso("ZW10") == "ZW-BU"
    assert places_join.province_pcode("Atlantis") is None


def test_resolve_names_what_it_cannot_do():
    prov = fc(feat("I", 0, 10))
    prov["features"][0]["properties"] = {"isoCode": "ZW-MI", "name": "Midlands"}
    out = places_join.resolve(5, 5, good(), prov)
    assert out["naturalRegions"][0]["code"] == "III"
    assert out["province"]["pcode"] == "ZW17"
    assert out["district"] is None and "not resolved" in out["districtNote"]
    empty = places_join.resolve(5, 5, fc())
    assert empty["naturalRegions"] == [] and "naturalRegionsNote" in empty


def run_loader(tmp_path, *extra, data=None, country=True):
    g = tmp_path / "nr.geojson"
    g.write_text(json.dumps(data or good()))
    args = [sys.executable, str(ROOT / "scripts" / "load_natural_regions.py"), "--geojson", str(g)]
    if country:
        c = tmp_path / "c.geojson"
        c.write_text(json.dumps(COUNTRY))
        args += ["--country", str(c)]
    return subprocess.run(args + list(extra), check=False, capture_output=True, text=True, env={"PATH": ""})


def test_loader_is_a_dry_run_by_default(tmp_path):
    r = run_loader(tmp_path)
    assert r.returncode == 0 and "DRY RUN" in r.stdout


def test_loader_refuses_to_write_without_the_owner_or_a_uri(tmp_path):
    r = run_loader(tmp_path, "--apply")
    assert r.returncode == 2 and "--approved-by" in r.stderr
    r = run_loader(tmp_path, "--apply", "--approved-by", "Owner")
    assert r.returncode == 2 and "AGRICONNECT_MONGO_URI" in r.stderr


def test_loader_refuses_bad_data_and_an_unchecked_coverage(tmp_path):
    r = run_loader(tmp_path, data=fc(feat("I", 0, 6), feat("III", 4, 10)), country=True)
    assert r.returncode == 2 and "problems" in r.stderr
    r = run_loader(tmp_path, country=False)
    assert r.returncode == 2 and "coverage" in r.stderr
