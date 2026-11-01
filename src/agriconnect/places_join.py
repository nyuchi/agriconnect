"""Join a place to its Natural Region, province and district P-code.

Provinces: `places.placesGeo` carries the ten provinces with an ISO 3166-2 `isoCode`
(ZW-BU ...), and `agriculture.adminAreas` carries the same ten with OCHA COD-AB
P-codes (ZW10 ...). The two are joined by name, checked below against the data read
on 2026-11-01. There is no ISO 3166-2 to P-code rule, so the table is explicit.

Districts: `agriculture.adminAreas` holds the 91 districts (level 2) with names and
`parentPcode`, but no geometry, and `placesGeo` holds no districts. A point cannot be
placed in a district until district boundaries exist in `places` (owner decision, see
docs/place-to-region.md). Until then `district` is None and says why.
"""

from __future__ import annotations

from typing import Any

from . import regions

#: ISO 3166-2 code, OCHA COD-AB P-code, name (identical in both collections).
PROVINCES: tuple[tuple[str, str, str], ...] = (
    ("ZW-BU", "ZW10", "Bulawayo"),
    ("ZW-MA", "ZW11", "Manicaland"),
    ("ZW-MC", "ZW12", "Mashonaland Central"),
    ("ZW-ME", "ZW13", "Mashonaland East"),
    ("ZW-MW", "ZW14", "Mashonaland West"),
    ("ZW-MN", "ZW15", "Matabeleland North"),
    ("ZW-MS", "ZW16", "Matabeleland South"),
    ("ZW-MI", "ZW17", "Midlands"),
    ("ZW-MV", "ZW18", "Masvingo"),
    ("ZW-HA", "ZW19", "Harare"),
)
_BY_ISO = {iso: (pc, name) for iso, pc, name in PROVINCES}
_BY_NAME = {name.lower(): (iso, pc) for iso, pc, name in PROVINCES}

PCODE_STANDARD = "OCHA COD-AB P-codes (HDX cod-ab-zwe, validOn 2018-09-11)"
PCODE_LICENCE = "CC-BY-IGO"


def province_pcode(iso_or_name: str) -> str | None:
    """P-code for an ISO 3166-2 code (`ZW-MI`) or a province name (`Midlands`)."""
    if iso_or_name in _BY_ISO:
        return _BY_ISO[iso_or_name][0]
    hit = _BY_NAME.get(iso_or_name.strip().lower())
    return hit[1] if hit else None


def province_iso(pcode_or_name: str) -> str | None:
    for iso, pc, name in PROVINCES:
        if pcode_or_name in (pc, name):
            return iso
    return None


def resolve(
    lon: float,
    lat: float,
    natural_regions: dict[str, Any],
    provinces: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Everything known about a point, each part with its source and licence.

    `provinces` is a FeatureCollection of province polygons with `isoCode` in
    properties (from places.placesGeo). Anything not found is None with a reason,
    never a guess.
    """
    out: dict[str, Any] = {"point": {"type": "Point", "coordinates": [lon, lat]}}
    matches = regions.lookup(natural_regions, lon, lat)
    out["naturalRegions"] = [
        {
            "code": m.code,
            "label": m.label,
            "classification": m.classification,
            "vintage": m.vintage,
            "source": m.source,
            "licence": m.licence,
            "attribution": m.attribution,
        }
        for m in matches
    ]
    if not matches:
        out["naturalRegionsNote"] = "no Natural Region polygon contains this point (or none is loaded)"

    out["province"] = None
    if provinces:
        for f in provinces.get("features", []):
            if regions.contains(f["geometry"], lon, lat):
                iso = f["properties"].get("isoCode")
                pc = province_pcode(iso) if iso else None
                out["province"] = {
                    "isoCode": iso,
                    "pcode": pc,
                    "name": f["properties"].get("name"),
                    "pcodeStandard": PCODE_STANDARD,
                    "pcodeLicence": PCODE_LICENCE,
                }
                break
    out["district"] = None
    out["districtNote"] = (
        "districts are not resolved: no district boundaries are held in places or agriculture "
        "(adminAreas has names and P-codes only)"
    )
    return out
