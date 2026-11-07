# ADR: one place layer for every surface

Refs #2. Status: **proposed; needs the owner's decision.** Owner direction (relayed by the
orchestrating session, 2026-11-01, not yet confirmed in this session by the owner's own message):
places is the world-around-us knowledge graph; Natural Regions belong there, not in `agriculture`;
AgriConnect, Servers API and Nyuchi API are views of one source; no silos.

## Context

The same geography is held in several places with different keys. Counts below were read from the
live Data MCP on 2026-11-01. Repos other than agriconnect and fly-mcp were not attached, so rows
marked `?` are unverified.

### The diff (duplication audit)

| What                            | Where                                                          | Keyed by                                       | Source                                        | Count                                     | Differs from `places`                                                                       | Recommended convergence                                                                                                                                                                                                                            |
| ------------------------------- | -------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Countries, provinces, 'city'    | `places.placesGeo`                                             | UUID `_id`, `slug` (`{name}-{ref}`), `isoCode` | Natural Earth 10m + user creations            | provinces 820 (all countries), 'city' 693 | The reference. Zimbabwe provinces have ISO 3166-2, **no P-codes**, no districts or wards    | Keep as the canonical place graph                                                                                                                                                                                                                  |
| Admin areas L1-L2               | `agriculture.adminAreas`                                       | `pcode` (OCHA)                                 | HDX cod-ab-zwe, CC-BY-IGO, validOn 2018-09-11 | 10 + 91, **no geometry**                  | A second province list, with the P-codes places lacks, and the only list of districts       | **Migrate**: P-codes become `identifier`s on `placesGeo` provinces; districts (and wards, from the same COD-AB file) become `placesGeo` children with geometry. Then delete `adminAreas` and reference by place id. Owner decision (places writer) |
| Natural Regions                 | nowhere                                                        | none                                           | no licensed polygon found                     | 0                                         | Missing                                                                                     | **Create in places** as versioned sets (`vincent-thomas-1960`, `agez-revision-2020`); never copy into other domains                                                                                                                                |
| Continent boxes                 | `weather.regions`                                              | `id` (`africa`...)                             | hand-set bbox                                 | 10                                        | Bounding boxes named like regions, not places                                               | Reference places continents, or rename to `viewports` so they are not mistaken for places. Owner decision                                                                                                                                          |
| Seasons                         | `weather.seasons` (also `placeKnowledge.seasons`)              | `countryCode`, month list                      | seed                                          | ?                                         | Season names are per country, copied into each place's knowledge doc                        | Keep one; `placeKnowledge` references it                                                                                                                                                                                                           |
| Climate normals                 | `weather.climate_normals`                                      | place-ish key                                  | ERA5                                          | 209                                       | `placeKnowledge.climate.normals` holds the same ERA5 normals per place (Gweru, Harare, ...) | Keep one store keyed by place id; the other references it                                                                                                                                                                                          |
| Airports / stations             | `weather.airports`, `weather.stations`, `agriculture.stations` | ICAO/IATA, WIGOS                               | OurAirports?, WIS2                            | 352, 1, 19                                | Three station/airport lists, none linked to a place id                                      | Each becomes a place with `sameAs` WIGOS/ICAO ids; domains hold only observations keyed by place id                                                                                                                                                |
| Place knowledge                 | `places.placeKnowledge`                                        | `name`, `placeCollection`, `geo`               | GEOGLAM, ERA5, seed                           | ?                                         | Keyed by name + collection, not by the `placesGeo` `_id`                                    | Key by place id                                                                                                                                                                                                                                    |
| Static seed catalogue           | mukoko-weather `src/lib/locations*.ts`, `countries.ts`         | local ids                                      | hand-written                                  | ?                                         | A third place list inside an app                                                            | **Delete**; resolve through the place resolver. Not verified (repo not attached)                                                                                                                                                                   |
| Kweli / events / news geography | ?                                                              | ?                                              | ?                                             | ?                                         | Not checked                                                                                 | Audit when attached                                                                                                                                                                                                                                |
| Doris / Postgres copies         | ?                                                              | ?                                              | ?                                             | ?                                         | Not checked                                                                                 | Audit when attached                                                                                                                                                                                                                                |
| User-created 'city' entries     | `placesGeo` `geoType: city`                                    | uuid                                           | user input                                    | 693                                       | Streets and shops typed as cities (for example "Windsor Avenue", "A14")                     | Retype by category or move to venues; owner decision, do not bulk edit                                                                                                                                                                             |

Sizes agree with what the orchestrator reported except that `placesGeo` has grown to 2,276
documents (other countries are loaded now), so the earlier "21 city entries" figure is stale for the
whole collection; the 21 were Zimbabwe's.

## Decision proposed

1. **One identifier.** A place is referred to by its `placesGeo` `_id` (UUID). Slugs
   (`{name}-{ref}`) are for URLs only. Standard identifiers are returned with every place as
   schema.org `identifier`/`sameAs`: ISO 3166-1/-2, OCHA P-code, WIGOS, ICAO/IATA, Wikidata and
   GeoNames ids where they exist.
2. **Natural Regions are places.** Each is an `AdministrativeArea`-like place (schema.org
   `Place` with `geo` as `GeoShape`/GeoJSON, RFC 7946) with `placeType: natural-region`,
   `classification`, `vintage`, `source`, `licence`, `attribution`, and a `containedInPlace`
   link to Zimbabwe. The two classifications are separate sets, not edits of each other.
3. **One resolver.** `resolve(lat, lon | placeId)` returns containing places by type (country,
   province, district, ward, natural region), each with ids, source and licence. Servers API,
   Nyuchi API and AgriConnect all call that resolver (one `$geoIntersects` query on the `2dsphere`
   index) and none keeps a list of its own.
4. **Domains reference, never copy.** `agriculture`, `weather`, `news`, `events`, `kweli` store a
   place id and their own facts.
5. **Guardrails.** A shared schema (JSON Schema/OpenAPI 3.1) for place references, and a test in each
   consuming repo that fails when a place list, bounding-box table or region constant is added.
   `tests/test_regions.py` shows the style for the geometry side.

### Options considered

| Option                                                                     | Trade-off                                                                                                                                                                |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A. Natural Regions in `agriculture.naturalRegions` (what PR #3 first did)  | Fast; a silo, and weather or news cannot reuse it. **Rejected** by the direction above                                                                                   |
| B. Natural Regions in `places` through the sanctioned writer (recommended) | One graph, one resolver; needs the places writer and may need a validator change for `placeType`, which must not be done without backup and rollback stated in the issue |
| C. A new `geography` domain                                                | Clean ownership, but a second place store beside `places`; contradicts "never build silos"                                                                               |

### Consequences

- The loader (`scripts/load_natural_regions.py`) no longer has a default target; its `--database`
  and `--collection` are explicit, and the real target is decided by this ADR.
- `agriculture.adminAreas` and the P-code join in `places_join.py` become temporary.
- No data moves until the owner picks B and the places writer is available.

## Needs the owner

1. Choose B (or say otherwise).
2. Approve P-codes, districts and wards into `placesGeo` from OCHA COD-AB, and any validator
   change (the issue must first state the change, a backup and a rollback).
3. Decide fate of `weather.regions` and the 'city' entries that are streets and shops.
4. Attach `data-infra`, `nyuchi-servers-api`, `nyuchi-api`, mukoko-weather so the `?` rows and the
   standards register can be checked.

## Update 2026-11-02: decisions relayed from the orchestrating session

1. **Places home: yes.** Natural Regions and the place contract belong to the `places` domain;
   `agriculture` references them by id. Option B is therefore the working choice (relayed by the
   orchestrator; the owner's own confirmation in this session is still pending).
2. **No production write is needed or authorised.** The loader stays dry-run-only in practice.
3. **Polygon source: open.** Status is "needs the ministry map or a licensed polygon". MSD, the
   Ministry and others publish no reuse terms (shamwari#149); permission emails are drafted on
   shamwari#148. Nothing waits on this: the model, loader and verification are specified as code
   with tests.

## Changes needed in `nyuchi/data-infra` (not attachable from this session; not verified against the repo)

Listed precisely so a data-infra session can apply them. Names are proposals; match the repo's
existing conventions where they differ.

| Where                    | Change                                                                                                                                                                                                                                                                                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `schemas/model` (LinkML) | A `NaturalRegion` class (a `Place` subtype): `code` (enum I, IIa, IIb, III, IV, V), `classification` (enum `vincent-thomas-1960`, `agez-revision-2020`), `vintage` (integer year), `rainfall_band_mm`, `source`, `licence`, `attribution`, `retrievedAt`, `geometry` (GeoJSON Polygon/MultiPolygon, RFC 7946), `containedInPlace` (place id) |
| `schemas/model`          | A `PlaceIdentifier` slot on `Place` (`scheme`, `value`): `iso3166-2`, `ocha-pcode`, `wigos`, `icao`, `iata`, `wikidata`, `geonames`, mapped to schema.org `identifier`/`sameAs`                                                                                                                                                              |
| places schema            | `geoType`/`placeType` value `natural-region`; district and ward types; the `places` validator is **not** changed by this repo, and any change needs backup and rollback stated in the issue first                                                                                                                                            |
| Standards register       | Entries for: GeoJSON RFC 7946 (exists?), schema.org `Place`/`GeoShape`, OCHA COD-AB P-codes (CC-BY-IGO), ISO 3166-2, WIGOS station id, Wikidata/GeoNames as `sameAs`                                                                                                                                                                         |
| `schemas/domains.yaml`   | None: `agriculture` is already listed; Natural Regions go in `places`. `scripts/domains/check_domains.py` needs no exception                                                                                                                                                                                                                 |
| Projection               | Publish `places` natural-region and admin-area sets to Doris so AgriConnect reads them there, not from a second Mongo copy                                                                                                                                                                                                                   |
| Licences register        | `CC-BY-IGO` (OCHA, WFP) added if AgriConnect or the commons are to serve them; currently only `CC-BY-4.0` is on AgriConnect's allowlist                                                                                                                                                                                                      |

Source of truth for Natural Regions licences: **open** until a ministry map with written permission
or a licensed polygon exists.
