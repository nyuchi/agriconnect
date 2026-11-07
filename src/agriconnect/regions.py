"""Natural Regions as reference geography: the GeoJSON model, its checks, and the lookup.

Zimbabwe's Natural Regions (farming zones I, IIa, IIb, III, IV, V) come in two
classifications that farmers mix up: the 1960 Vincent and Thomas map and the 2020
reclassification. Both are kept, told apart by `classification` and `vintage`.

This is reference geography, not a served aggregate, so it is outside the k>=10
rule in `policy.py` (there are no records about people in it). It still carries a
`licence` and an `attribution` on every feature, and nothing is loaded whose
licence has not been read and recorded.

GeoJSON follows RFC 7946 (WGS 84, longitude then latitude, right-hand rule).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

CODES = ("I", "IIa", "IIb", "III", "IV", "V")
#: `1960` is Vincent and Thomas (with II split into IIa/IIb); `2020` is the
#: Government of Zimbabwe AEZ revision (ZINGSA, Manatsa et al.). Vintage is the year
#: of the map itself, so a later re-issue of the same map is a different vintage.
CLASSIFICATIONS = ("vincent-thomas-1960", "agez-revision-2020")
CLASSIFICATION_VINTAGE = {"vincent-thomas-1960": 1960, "agez-revision-2020": 2020}
REQUIRED_PROPERTIES = (
    "code",
    "label",
    "classification",
    "vintage",
    "rainfall_band_mm",
    "source",
    "licence",
    "attribution",
    "retrievedAt",
)
#: Licences under which a polygon may be redistributed. A load with any other value is
#: refused: "unknown" or "all rights reserved" must never reach the shared database.
REDISTRIBUTABLE_LICENCES = frozenset(
    {"CC0-1.0", "CC-BY-4.0", "CC-BY-IGO", "ODbL-1.0", "public-domain"}
)
#: Overlap beyond this fraction of the smaller region's area is a defect. Digitised
#: boundaries share edges, so a sliver is normal; a large overlap is not.
OVERLAP_TOLERANCE = 0.001
#: A classification must cover at least this fraction of the country boundary.
COVERAGE_MIN = 0.99


class RegionError(ValueError):
    """The feature collection breaks the model."""


@dataclass(frozen=True)
class Match:
    code: str
    label: str
    classification: str
    vintage: int
    source: str
    licence: str
    attribution: str


def _ring_ok(ring: Any) -> str | None:
    if not isinstance(ring, list) or len(ring) < 4:
        return "a ring needs at least 4 positions"
    if ring[0] != ring[-1]:
        return "a ring must be closed"
    for p in ring:
        if (
            not isinstance(p, (list, tuple))
            or len(p) < 2
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p[:2])
            or not (-180 <= p[0] <= 180 and -90 <= p[1] <= 90)
        ):
            return f"position out of range or swapped (lon, lat expected): {p}"
    return None


def _signed_area(ring: list) -> float:
    return sum(
        (ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]) for i in range(len(ring) - 1)
    ) / 2


def _polygons(geometry: dict) -> list[list[list[list[float]]]]:
    t = geometry.get("type")
    coords = geometry.get("coordinates")
    if t == "Polygon":
        polys = [coords]
    elif t == "MultiPolygon":
        polys = list(coords or [])
    else:
        raise RegionError(f"geometry must be Polygon or MultiPolygon, not {t!r}")
    if not polys or any(not isinstance(p, list) or not p for p in polys):
        raise RegionError("a polygon needs at least an exterior ring")
    return polys


def check_collection(fc: dict[str, Any]) -> list[str]:
    """Structural problems, without any geometry library. Empty means well formed and
    safe to look up in."""
    out: list[str] = []
    if not isinstance(fc, dict) or fc.get("type") != "FeatureCollection":
        return ["not a FeatureCollection"]
    features = fc.get("features")
    if not isinstance(features, list) or not features:
        return ["a FeatureCollection with no features"]
    seen: set[tuple[str, str, str]] = set()
    for i, f in enumerate(features):
        where = f"feature {i}"
        if not isinstance(f, dict):
            out.append(f"{where}: not an object")
            continue
        props = f.get("properties")
        if not isinstance(props, dict):
            out.append(f"{where}: properties must be an object")
            props = {}
        for k in REQUIRED_PROPERTIES:
            if props.get(k) in (None, ""):
                out.append(f"{where}: missing property {k}")
        if props.get("code") not in CODES:
            out.append(f"{where}: code {props.get('code')!r} is not one of {CODES}")
        cls = props.get("classification")
        if cls not in CLASSIFICATIONS:
            out.append(f"{where}: classification {cls!r} is unknown")
        vintage = props.get("vintage")
        if not isinstance(vintage, int) or isinstance(vintage, bool):
            out.append(f"{where}: vintage must be an integer year, not {vintage!r}")
        elif cls in CLASSIFICATION_VINTAGE and vintage != CLASSIFICATION_VINTAGE[cls]:
            out.append(f"{where}: {cls} has vintage {CLASSIFICATION_VINTAGE[cls]}, not {vintage}")
        if props.get("licence") and props["licence"] not in REDISTRIBUTABLE_LICENCES:
            out.append(f"{where}: licence {props['licence']!r} is not a known redistributable licence")
        key = (str(cls), str(vintage), str(props.get("code")))
        if key in seen:
            out.append(f"{where}: duplicate {key}")
        seen.add(key)
        try:
            for poly in _polygons(f.get("geometry") or {}):
                for r, ring in enumerate(poly):
                    bad = _ring_ok(ring)
                    if bad:
                        out.append(f"{where}: {bad}")
                    elif r == 0 and _signed_area(ring) < 0:
                        out.append(f"{where}: exterior ring is clockwise (RFC 7946 needs counter-clockwise)")
                    elif r > 0 and _signed_area(ring) > 0:
                        out.append(f"{where}: a hole is counter-clockwise (RFC 7946 needs clockwise)")
        except (RegionError, TypeError, AttributeError) as e:
            out.append(f"{where}: {e}")
    return out


def _on_segment(x: float, y: float, a: list, b: list) -> bool:
    cross = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
    if abs(cross) > 1e-12:
        return False
    return min(a[0], b[0]) - 1e-12 <= x <= max(a[0], b[0]) + 1e-12 and (
        min(a[1], b[1]) - 1e-12 <= y <= max(a[1], b[1]) + 1e-12
    )


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    """Ray casting, boundary inclusive: a point on an edge is inside, so a point on a
    shared edge matches both neighbours and the caller sees the ambiguity."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        if _on_segment(x, y, ring[j], ring[i]):
            return True
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def contains(geometry: dict, lon: float, lat: float) -> bool:
    """Point in Polygon/MultiPolygon: inside the outer ring and not inside a hole."""
    for poly in _polygons(geometry):
        if _point_in_ring(lon, lat, poly[0]) and not any(
            _point_in_ring(lon, lat, h) and not any(
                _on_segment(lon, lat, h[k], h[k + 1]) for k in range(len(h) - 1)
            )
            for h in poly[1:]
        ):
            return True
    return False


def lookup(
    fc: dict[str, Any],
    lon: float,
    lat: float,
    classification: str | None = None,
) -> list[Match]:
    """The Natural Region(s) at a point, one per classification (or the one asked for).

    A point on a shared edge may match two regions of one classification; both are
    returned so the caller sees the ambiguity instead of a silent pick.
    """
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise RegionError("lon must be in [-180, 180] and lat in [-90, 90] (lon first)")
    out: list[Match] = []
    for f in fc.get("features", []):
        p = f["properties"]
        if classification and p["classification"] != classification:
            continue
        if contains(f["geometry"], lon, lat):
            out.append(
                Match(
                    p["code"],
                    p["label"],
                    p["classification"],
                    int(p["vintage"]),
                    p["source"],
                    p["licence"],
                    p["attribution"],
                )
            )
    return out


def verify(
    fc: dict[str, Any],
    country: dict[str, Any] | None = None,
    overlap_tolerance: float = OVERLAP_TOLERANCE,
    coverage_min: float = COVERAGE_MIN,
) -> dict[str, Any]:
    """Counts, valid geometry, overlaps within tolerance, coverage of the country.

    Needs `shapely` (the `geo` extra) for the geometry checks. `country` is a
    Polygon/MultiPolygon geometry or a Feature of one (Zimbabwe's boundary from
    places.placesGeo, Natural Earth 10m).
    """
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from shapely.validation import explain_validity

    problems = check_collection(fc)
    report: dict[str, Any] = {
        "features": len(fc.get("features", [])) if isinstance(fc, dict) else 0,
        "by_classification": {},
    }
    if problems:
        # Structural problems make geometry checks meaningless (and unsafe to run).
        report["problems"] = problems
        report["ok"] = False
        return report
    groups: dict[tuple[str, int], list[tuple[str, Any]]] = {}
    for f in fc.get("features", []):
        p = f["properties"]
        g = shape(f["geometry"])
        if not g.is_valid:
            problems.append(f"{p.get('code')}/{p.get('classification')}: invalid geometry: {explain_validity(g)}")
            continue
        groups.setdefault((p["classification"], int(p["vintage"])), []).append((p["code"], g))

    boundary = None
    if country is not None:
        geom = country.get("geometry", country)
        boundary = shape(geom)
        if not boundary.is_valid:
            problems.append("country boundary is invalid")
            boundary = None

    for (cls, vintage), items in sorted(groups.items()):
        entry: dict[str, Any] = {"regions": sorted(c for c, _ in items)}
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                (ca, ga), (cb, gb) = items[a], items[b]
                inter = ga.intersection(gb).area
                smaller = min(ga.area, gb.area)
                if smaller and inter / smaller > overlap_tolerance:
                    problems.append(f"{cls} {vintage}: {ca} and {cb} overlap by {inter / smaller:.4%}")
        if boundary is not None and boundary.area:
            cov = unary_union([g for _, g in items]).intersection(boundary).area / boundary.area
            entry["coverage"] = round(cov, 4)
            if cov < coverage_min:
                problems.append(f"{cls} {vintage}: covers {cov:.2%} of the country, below {coverage_min:.0%}")
        report["by_classification"][f"{cls}/{vintage}"] = entry
    report["problems"] = problems
    report["ok"] = not problems
    return report


def stamp(features: Iterable[dict]) -> list[dict]:
    """The Mongo document for each feature: GeoJSON geometry in `geometry` for the
    2dsphere index, properties flattened, and a deterministic `_id` so a load is
    idempotent."""
    docs = []
    for f in features:
        p = f["properties"]
        docs.append(
            {
                "_id": f"zw-nr-{p['classification']}-{int(p['vintage'])}-{p['code']}",
                "type": "Feature",
                "geometry": f["geometry"],
                "properties": p,
                "countryCode": "ZW",
            }
        )
    return docs
