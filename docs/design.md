# Design

## Why it exists

Weather, markets and places data already sits in the Nyuchi data layer. Most of
it is open in spirit and unusable in practice: scattered, not aggregated, and
mixed in with records that must never leave. AgriConnect is the one place that
decides what may be served, and proves it in code.

## Boundaries

- **Input:** a domain's Apache Doris database, read-only, over Fly 6PN.
- **Output:** aggregates only, each with its licence and its cell floor, to
  internal callers with one token.
- **Not here:** accounts, billing, personal data, writes. A caller that needs any
  of those is a different service.

## Alongside data-infra

data-infra's rule is that a domain is a namespace in every store, with its own
roles and credentials, and nothing is granted across domains. AgriConnect keeps
to it: one read-only login per domain it serves, no cross-domain grants. If the
data does not fit an existing domain, the domain list in data-infra changes
first.

## Shamwari

Shamwari's Ground can ingest AgriConnect's output as a source. That data is open,
so it may reach Cloud inference; it carries its own licence class for Mind
training and is not trainable until that is reviewed. Personal-scope data never
touches this service.

## The data comes first

AgriConnect serves what the data layer holds, to the standards the layer has
already adopted. Weather is the first candidate and is not ready: the live
`weather` database has 16 collections and about a thousand documents, with
ObjectIds, country names instead of ISO codes, two names for each quantity and
daily values keyed by an instant. The register adopts WMO 4677, WIGOS station
ids, CF Conventions 1.13 and Open-Meteo, and the fix is already written up as
[data-infra#90](https://github.com/nyuchi/data-infra/issues/90): model weather in
LinkML, back-fill it with UUIDs, ISO codes and one CF-named metric per quantity,
and publish the open commons to Doris. AgriConnect reads the Doris result. It
does not clean data itself.

## Not done

Real datasets, the domain, Doris login, the Fly app, the licence, and the link
into Shamwari's Ground.
