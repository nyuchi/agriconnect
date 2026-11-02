# Natural Regions as reference geography

Refs #2. See also `docs/adr-places-contract.md`: the home of this data is proposed to be the places domain, not agriculture. Status: **design plus tested loader. No real polygon is loaded, because no source with a
confirmed redistribution licence has been found.** Nothing here writes to production.

## Why it matters

Farmers say "Region 4". Advice on what to plant, and when, depends on the region more than on the
province. Two classifications are in use and they differ, so both are kept and told apart:

| `classification`      | `vintage` | What it is                                                                  |
| --------------------- | --------- | --------------------------------------------------------------------------- |
| `vincent-thomas-1960` | 1960      | Vincent and Thomas, five regions with II split into IIa/IIb                 |
| `agez-revision-2020`  | 2020      | Government of Zimbabwe AEZ revision (ZINGSA), which moved zones drier       |

## Sources checked, in the owner's order (retrieved 2026-11-01)

| Source | Licence (quoted) | Natural Region polygons? | Verdict |
| --- | --- | --- | --- |
| [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) | "All versions of _Natural Earth_ raster + vector map data found on this website are in the public domain." | No. The terms page lists no agro-ecological or farming-zone layer (the theme list was not enumerated). We already hold its admin-1 provinces (10m). | Use for the country and province boundary only. |
| OpenStreetMap via Overpass | Not fetched. OSM data is ODbL 1.0 (stated from knowledge, not verified here). | **Not checked.** `overpass-api.de` answered "connection reset by peer" from this sandbox's proxy on 2026-11-01. I did not try to bypass the proxy. | Open: run the query from a machine that can reach Overpass (below). |
| [BGS Zimbabwe Open GIS Data](https://zenodo.org/records/17425387) (Zenodo, v3, 2025-10-23) | "Creative Commons Attribution 4.0 International ... allows re-distribution and re-use of a licensed work on the condition that the creator is appropriately credited." | The page lists SRTM, Sentinel-2 and OSM vectors; natural regions are not mentioned. The 6.6 GB zip was not opened. | Not a source for regions as far as the page says. |
| [FAO, Zimbabwe natural regions table](http://www.fao.org/4/a0395e/a0395e06.htm) | No reuse statement visible. Table 1 cites "Moyo, 2000; Vincent and Thomas, 1961". | No. A descriptive table of rainfall and farming systems. | Cite for definitions only. It disagrees with itself (text says III is 500-750 mm, table says 500-800; text says V is under 650 mm, table says under 450), so `rainfall_band_mm` is not filled from it. |
| Surveyor-General, "Zimbabwe natural regions and provisional farming areas: boundaries as at 1st July, 1997" ([Yale catalogue](https://geoblacklight.library.yale.edu/catalog/bibid-4750842)) | Not stated in the listing. | A paper map record, no download. | Do not use until the Surveyor-General confirms rights. |
| 2020 reclassification: [AEZ2020 report](https://ir.library.msu.ac.zw/handle/11408/5282), [Mugandani et al. 2012](https://ir.library.msu.ac.zw/handle/11408/4489) (MSU repository) | **Unread.** The repository pages returned only a site title to my fetch. | Unknown whether boundary files are published. | Ask the authors/ZINGSA (below). |
| ISRIC Zimbabwe atlas | **Unread.** No Zimbabwe atlas terms were found. | Unknown. | Ask ISRIC if the owner wants this route. |
| WFP/HDX "ICA Zimbabwe - Predominant Livelihood Zones" | Not read. | No: livelihood zones, not Natural Regions. | Not the right dataset. |

**Result:** there is no polygon I can legally copy today. I did not digitise from a scanned map; that
needs the owner's say-so.

### Decisions for the owner

1. Ask ZINGSA / the AEZ2020 authors for the boundary layer and its licence (best fit: the 2020 and
   the 1960 layers come from the same study).
2. Or approve digitising the 1960 map by hand (the map is the 1961 Vincent and Thomas publication;
   check its copyright status first, and record the digitiser and method as `source`).
3. Meanwhile, run this from a machine that can reach Overpass and send the result back; it only
   reads, and the Overpass usage policy asks for one query, cached, with an identifying
   User-Agent:

```text
[out:json][timeout:60];
area["ISO3166-1"="ZW"][admin_level=2]->.zw;
(
  nwr(area.zw)["boundary"="agro_ecological_zone"];
  nwr(area.zw)["zone"="natural_region"];
  nwr(area.zw)["name"~"Natural Region|Agro-?ecological",i];
);
out tags center;
```

## The model (GeoJSON, RFC 7946)

A `FeatureCollection` of `Polygon`/`MultiPolygon` features, WGS 84, longitude first. Every
feature carries:

| property           | meaning                                                                     |
| ------------------ | --------------------------------------------------------------------------- |
| `code`             | `I`, `IIa`, `IIb`, `III`, `IV`, `V`                                          |
| `label`            | for example "Natural Region III"                                             |
| `classification`   | `vincent-thomas-1960` or `agez-revision-2020`                                |
| `vintage`          | year of the map                                                              |
| `rainfall_band_mm` | as stated **by the map's own source**, not copied from a secondary summary    |
| `source`, `licence`, `attribution` | where it came from, under what terms, whom to credit        |
| `retrievedAt`      | date retrieved                                                               |

Proposed home: the places domain (see the ADR); the layout below is the same wherever it lives. One document per feature, `_id` =
`zw-nr-<classification>-<vintage>-<code>`), with a `2dsphere` index on `geometry`. `agriculture` is a data-infra domain (2026-10-28).

## Loader and verification

`scripts/load_natural_regions.py` (tests in `tests/test_regions.py`, synthetic squares only):

- **Dry run is the default.** It verifies and prints what it would write; it never opens a
  database connection.
- `verify` checks: required properties, known codes and classifications, a `vintage` that matches the
  classification, a licence on the redistributable list, no duplicates, closed rings with RFC 7946
  winding (exterior counter-clockwise, holes clockwise),
  longitude/latitude in range (catches swapped axes), valid geometry, pairwise overlap within
  0.1% of the smaller region, and at least 99% coverage of Zimbabwe's boundary per
  classification. A load with problems, or without the boundary to check coverage, is refused.
- `--apply` needs `--approved-by "<owner name>"`, the URI in `AGRICONNECT_MONGO_URI` (never argv),
  and a clean verification. It upserts by `_id`, so a re-run changes nothing (the approver is printed, not stored in the
  documents), and it never deletes.

Country boundary for the coverage check: the Zimbabwe country document in `places.placesGeo`
(Natural Earth 10m), exported as GeoJSON.

### The one exact command, for when a source and your yes exist

```bash
pip install -e '.[geo]'
python scripts/load_natural_regions.py --geojson natural-regions.geojson --country zimbabwe-boundary.geojson
# read the verify report; if "ok": true, then:
AGRICONNECT_MONGO_URI='<write-capable URI for the chosen database>' python scripts/load_natural_regions.py \
  --geojson natural-regions.geojson --country zimbabwe-boundary.geojson \
  --database <db> --collection <collection> --apply --approved-by "Bryan Fawcett"
```

Not run. The Data MCP is read-only by design; this write is a separate, owner-held step.
