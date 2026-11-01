# Draft: Servers API read routes for agriculture

Refs #2. **Draft contract only. Nothing is built.** Written without access to
`nyuchi-servers-api` (not attached to this session) or its issue #23; reconcile with that repo's
contract style before use. Internal, no public IP, read-only, `GET` only.

## Rules

- Every answer carries `source`, `licence`, `attribution`, `retrievedAt` and `method`
  (`observed`, `modelled`, `derived`, `seed`, `unverified`). No bare numbers.
- A value that is not known is `null` with a `note`; it is never estimated.
- Errors are RFC 9457 `application/problem+json`. OpenAPI 3.1 describes every route.
- Personal data never appears: these routes carry reference geography and open aggregates only.
- Coordinates are GeoJSON order, `lon` then `lat`.

## Routes

| Route | Purpose |
| --- | --- |
| `GET /v1/agriculture/resolve?lat=&lon=` or `?placeId=` | Natural Region(s) (both classifications), province (ISO 3166-2 + P-code), district (null until boundaries exist) |
| `GET /v1/agriculture/natural-regions?classification=&code=` | The region definitions and, with `Accept: application/geo+json`, the GeoJSON |
| `GET /v1/agriculture/calendar?placeId=&crop=` | Planting / vegetative / harvest day-of-year windows from `places.placeKnowledge.agriculture` (GEOGLAM CM4EW v1.3) |
| `GET /v1/agriculture/rainfall/{pcode}?from=&to=` | Dekadal rainfall for a province from `agriculture.rainfallDekadal` (CHIRPS via WFP) |
| `GET /v1/agriculture/datasets` | The agriculture catalogue entries with licence and status |

### `resolve` response (200)

```json
{
  "data": {
    "naturalRegions": [{"code": "III", "classification": "vincent-thomas-1960", "vintage": 1960}],
    "province": {"isoCode": "ZW-MI", "pcode": "ZW17", "name": "Midlands"},
    "district": null
  },
  "sources": [
    {"field": "naturalRegions", "source": "...", "licence": "...", "attribution": "...", "retrievedAt": "...", "method": "observed"},
    {"field": "province", "source": "places.placesGeo (Natural Earth 10m); P-code from OCHA COD-AB (HDX cod-ab-zwe)", "licence": "CC-BY-IGO", "method": "observed"}
  ],
  "notes": ["district: no district boundaries are held"]
}
```

(Values for `naturalRegions` are illustrative; no polygon is loaded yet.)

### Errors (RFC 9457)

| Status | `type` | When |
| --- | --- | --- |
| 400 | `/problems/invalid-coordinates` | lat/lon missing, not numbers, out of range, or swapped |
| 404 | `/problems/place-not-found` | unknown `placeId` |
| 404 | `/problems/outside-coverage` | point is outside Zimbabwe |
| 409 | `/problems/data-not-loaded` | the requested layer (for example Natural Regions) is not loaded yet |
| 429 | `/problems/rate-limited` | IETF `RateLimit` headers set |
| 503 | `/problems/store-unavailable` | database not reachable; no partial answer |

## Data access

`resolve` is one `$geoIntersects` against `agriculture.naturalRegions` (2dsphere) and one against
the province polygons in `places.placesGeo`. All reads are read-only; permissions mirror the
Data MCP's `data:read` view (personal fields masked, which none of these collections hold).
