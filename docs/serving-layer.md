# Who serves agriculture to Shamwari: a recommendation, not a decision

Refs #2. **The owner has not decided.** This sets out the trade-offs and a design that works with
either choice.

## The two candidates

|                             | AgriConnect (this repo)                                                                                         | Servers API read routes (`nyuchi-servers-api`)                                                                                   |
| --------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Best for                    | Open, aggregated datasets for people and partners; feeds the `/v1/open-data` commons (DCAT v3, CSVW, CC BY 4.0) | Lookups Shamwari and Core call mid-conversation: place to region, calendar, rainfall                                             |
| Data path                   | Reads Doris read-only, k >= 10 rule, CC-BY-4.0 allowlist                                                        | Reads Mongo/Doris as the one internal gateway; "only Nyuchi API and Servers API may touch databases, and Core goes through them" |
| Fit for reference geography | Poor: the rule is about aggregates of records, and Natural Regions are not records                              | Good: a point lookup with source and licence                                                                                     |
| Fit for open aggregates     | Good: that is its purpose                                                                                       | Duplicates the commons if it also publishes them                                                                                 |
| Exposure                    | No public address, one bearer token                                                                             | Internal, no public IP                                                                                                           |
| Cost to build now           | Exists as scaffold (PR #1)                                                                                      | Route contract only (draft below); service not built here                                                                        |

## Recommendation

1. **Servers API serves Shamwari and Core** the small set of lookups in
   `docs/servers-api-contract.md`: that is where the platform already says database access sits.
2. **AgriConnect stays the producer of open aggregates** for the commons (rainfall by province,
   FAOSTAT production, prices once licences clear) and never serves a second catalogue.
3. **One source of truth:** the `agriculture` Mongo database (reference and facts) is read by
   Servers API directly; AgriConnect reads the Doris copy that the publish pipeline produces from
   it. Neither copies the other's data, and the `2dsphere` lookup is the same query in both.
4. Revisit if Shamwari needs open aggregates in conversation: then it calls the commons, not
   AgriConnect directly.

## What needs your decision

- Confirm the split above, or pick one layer.
- AgriConnect's rule (`policy.py`) allows CC-BY-4.0 only and demands k >= 10 records. Several
  agriculture sources are CC-BY-IGO (OCHA boundaries, WFP prices) or are already-aggregated
  satellite/area statistics with no record count. Allowing CC-BY-IGO or defining a
  "published-aggregate" kind is a **policy change**: I have not touched `policy.py`.
- Whether AgriConnect needs a `staging` branch (AGENTS.md says PRs target `staging`; only `main`
  exists, as PR #1 already notes).

## Honest limits

I could not read `nyuchi-servers-api` or `nyuchi-api` (attaching them was blocked in this session), so
the contract is written without seeing their conventions or issue #23; it must be reconciled with
them before anyone builds it.
