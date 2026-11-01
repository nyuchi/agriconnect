# Place to region

Refs #2. Code: `src/agriconnect/places_join.py` and `regions.lookup` (tested).

Input: a latitude/longitude, or a `places.placesGeo` place (its `geo` point). Output, each part
with its source and licence, and `null` plus a reason when unknown:

```json
{
  "point": {"type": "Point", "coordinates": [29.8, -19.45]},
  "naturalRegions": [
    {"code": "...", "classification": "vincent-thomas-1960", "vintage": 1960, "source": "...", "licence": "..."},
    {"code": "...", "classification": "agez-revision-2020", "vintage": 2020, "source": "...", "licence": "..."}
  ],
  "province": {"isoCode": "ZW-MI", "pcode": "ZW17", "name": "Midlands"},
  "district": null,
  "districtNote": "districts are not resolved: no district boundaries are held ..."
}
```

Both classifications come back side by side, never merged.

## Provinces: verified join (data read 2026-11-01)

`places.placesGeo` provinces carry an ISO 3166-2 `isoCode`; `agriculture.adminAreas` (level 1, OCHA
COD-AB, licence CC-BY-IGO) carries P-codes. They match by name, one to one:

| ISO 3166-2 | P-code | Province           | ISO 3166-2 | P-code | Province           |
| ---------- | ------ | ------------------ | ---------- | ------ | ------------------ |
| ZW-BU      | ZW10   | Bulawayo           | ZW-MN      | ZW15   | Matabeleland North |
| ZW-MA      | ZW11   | Manicaland         | ZW-MS      | ZW16   | Matabeleland South |
| ZW-MC      | ZW12   | Mashonaland Central| ZW-MI      | ZW17   | Midlands           |
| ZW-ME      | ZW13   | Mashonaland East   | ZW-MV      | ZW18   | Masvingo           |
| ZW-MW      | ZW14   | Mashonaland West   | ZW-HA      | ZW19   | Harare             |

## Districts: not resolvable yet

`agriculture.adminAreas` holds the 91 districts (level 2) with names and `parentPcode`, but **no
geometry**. `placesGeo` holds no districts. So a point can reach its province but not its district
until district boundaries exist. Until then the answer says so; it does not guess from a name.

### Adding districts and wards through the sanctioned path (owner decision)

1. Source: OCHA COD-AB Zimbabwe (HDX `cod-ab-zwe`, listed in `agriculture.datasets` as loaded,
   formats XLSX/SHP/GeoJSON/GDB, licence CC-BY-IGO, validOn 2018-09-11) has levels 0-3
   (country, province, district, ward) with P-codes. Confirm the ward count (1,961 in your note)
   against the file.
2. Load into `places.placesGeo` as `geoType: district` / `ward`, `parentPlaceId` to the province /
   district, `pcode` and `isoCode`-style identifiers, `dataOrigin: ocha_cod_ab`, through the
   sanctioned places writer, with the validator unchanged unless you decide it must change.
3. Attribution travels with each document (CC-BY-IGO requires it).
4. Then `places_join.resolve` gets a district polygon set exactly as it gets provinces.

Nothing in this repo writes to `places`.

## Lookup in the database, not in two code bases

With the `2dsphere` index on `agriculture.naturalRegions.geometry`, the lookup is one query,
`find({geometry: {$geoIntersects: {$geometry: <Point>}}})`, so Servers API (Rust) and AgriConnect
(Python) use the same data and the same answer without sharing code. `regions.lookup` is the
pure-Python reference implementation and the test oracle.
