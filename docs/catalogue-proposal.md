# Proposed first catalogue entries (for the owner to approve)

Refs #2. **Nothing here is enabled and nothing is applied.** This is a diff for review. Facts are
from `agriculture.datasets` and the collections read on 2026-11-01.

## What blocks each candidate

| Candidate                         | Licence in `agriculture.datasets` | On the allowlist (`CC-BY-4.0` only)? | Status                                        | Blocker                                                |
| --------------------------------- | --------------------------------- | ------------------------------------ | --------------------------------------------- | ------------------------------------------------------ |
| Admin areas (OCHA COD-AB)         | CC-BY-IGO                         | **No**                               | loaded in Mongo                               | Allowlist change (policy) or serve outside AgriConnect |
| Natural Regions                   | not yet known                     | No                                   | no polygons                                   | Source and licence (see `natural-regions.md`)          |
| Rainfall by province (WFP/CHIRPS) | CC-BY-4.0                         | Yes                                  | partially loaded (10 provinces, from 2025-10) | Doris copy; approver; k rule                           |
| FAOSTAT crop production           | CC-BY-4.0                         | Yes                                  | partially loaded (12 observations)            | Doris copy; approver; k rule                           |
| WFP food prices (27,872 rows)     | CC-BY-IGO                         | **No**                               | queued for loader                             | Allowlist change; licence read                         |
| FEWS NET classification           | CC-BY-4.0                         | Yes                                  | catalogue only                                | Loader                                                 |
| Three FAOSTAT datasets            | `null`                            | No                                   | catalogue only                                | Licence unknown, so not open                           |

Two structural points the owner should decide, not me:

1. **The data is in Mongo; AgriConnect reads Doris.** Each entry needs a published Doris table
   first (data-infra publish pipeline).
2. **The k >= 10 rule counts records.** Rainfall and prices here are already published area
   aggregates; there is no record count to check. Either the policy gets a "published aggregate"
   kind with its own check, or these are not AgriConnect datasets. I have not changed
   `policy.py`.

## Diff for `catalogue/datasets.yaml` (disabled, not applied)

```diff
   - id: example-rainfall
     ...
+
+  # Proposed. enabled: false and approved_by: null until the owner names an approver.
+  - id: zw-rainfall-dekadal-province
+    title: Zimbabwe rainfall by province, 10-day totals (CHIRPS via WFP)
+    domain: agriculture
+    database: agriculture
+    table: rainfall_dekadal            # Doris copy, to be published; source is Mongo agriculture.rainfallDekadal
+    licence: CC-BY-4.0
+    open: true
+    enabled: false
+    approved_by: null
+    min_cell_size: 10                  # placeholder: see structural point 2
+    columns:
+      - {name: pcode, kind: dimension}               # OCHA P-code ZW10..ZW19
+      - {name: dekad_start, kind: dimension}         # ISO 8601 date
+      - {name: rfh_mm_per_dekad, kind: measure}      # mm per 10 days
+      - {name: rfh_long_term_avg_mm, kind: measure}  # long-term average, same dekad
+      - {name: rfq_percent_of_avg, kind: measure}
+      - {name: version, kind: dimension}             # f final, p preliminary
+
+  - id: zw-faostat-crop-production
+    title: Zimbabwe crop production, FAOSTAT (maize, millet, sorghum, wheat)
+    domain: agriculture
+    database: agriculture
+    table: observations                # partial: 12 documents, 1990-2024
+    licence: CC-BY-4.0
+    open: true
+    enabled: false
+    approved_by: null
+    min_cell_size: 10
+    columns: []                        # fill from the Doris schema once published
```

Entries **not** proposed until their blocker clears: admin areas and WFP prices (CC-BY-IGO), Natural
Regions (no source), the three null-licence FAOSTAT datasets.

Each served dataset also needs DCAT fields for the commons (`dct:license`, `dct:publisher`,
`bundu:kAnonymity`, `csvw:tableSchema`), as the README requires; the mapping is part of the
approved change, not this proposal.
