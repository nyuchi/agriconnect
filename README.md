# AgriConnect

Good decisions on the land start with good information, and most of it never
reaches the people who need it. AgriConnect takes open agricultural data from
the Nyuchi data layer and makes it easy to find and use, with no personal
information in it: what it serves is open, aggregated and checked before it
leaves.

It is **owned by Nyuchi** and built alongside
[nyuchi/data-infra](https://github.com/nyuchi/data-infra). Shamwari can read its
output as one more cited source, so a farmer's question about weather or markets
gets an answer with the source named.

**Status: scaffold.** The rule, the catalogue format, the Doris reader, the API
and the tests exist. No dataset is enabled, nothing is deployed, and no Fly app
has been created.

## Where it fits (do not duplicate the commons)

The platform already has an open-data commons: `/v1/open-data` in
`nyuchi/nyuchi-api`, a DCAT v3 JSON-LD catalogue with CSVW column schemas,
CC BY 4.0 data and a k-anonymity release check (`gateway/lib/anonymise.py`),
using `bundu:kAnonymity` from [vocab.bundu.org](https://vocab.bundu.org). Its
register entries are `dcat`, `csvw` and `cc_by_4`. AgriConnect is the
**producer** for the agriculture and weather domains: it builds releases that
pass this repository's rule and hands them to that commons. It does not run a
second catalogue with its own format, and its catalogue file should map to DCAT
fields (`dct:license`, `bundu:kAnonymity`, `csvw:tableSchema`) rather than
invent new ones. The wiring is not built yet.

## The rule

A dataset is served only when all of this holds (`src/agriconnect/policy.py`,
tested in `tests/`):

- it is marked **open**, with a licence on the allowlist (a licence nobody has
  reviewed counts as not open);
- a named person has **approved** it, and it is **enabled**;
- every column is declared. **Identifier and personal columns** (a person, a
  farm, a phone number, a precise location) may exist in the source table but are
  never selected, grouped or returned;
- every row served is an **aggregate of at least 10 records** (`K_MIN`), or more
  if the dataset asks. The query asks for this, and the response checks it again,
  so a small cell cannot point at one farm.

Each of these is a control with a test that fails if it is broken, not a note in
the catalogue.

## Layout

- `catalogue/datasets.yaml`: the datasets that may be served. One example,
  switched off.
- `src/agriconnect/policy.py`: the rule above.
- `src/agriconnect/source.py`: one aggregate query, and the read-only Doris
  reader.
- `src/agriconnect/app.py`: the API: `/health`, `/v1/datasets`,
  `/v1/datasets/{id}/series`.
- `Dockerfile`, `fly.toml`: the Fly app `nyuchi-agriconnect`, region `jnb`, no
  public address.

## Run the tests

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## How it connects

- **Reads** one domain's Doris database through a read-only login, over Fly's
  private network (`DORIS_HOST`, `DORIS_PORT`, `DORIS_USER`, `DORIS_PASSWORD`).
  It never writes.
- **Serves** other internal apps with one bearer token (`AGRICONNECT_TOKEN`). With
  no token set it answers 503 and nothing else.
- **No public address.** Like the apps in data-infra, it is reachable only from
  other Fly apps.

## Deploying

Deploys are manual, as in data-infra: `fly deploy --remote-only` from a checkout.
Creating the app, its secrets and its Doris login are owner steps. Nothing
deploys on merge.

## Open decisions

- Which Nyuchi datasets count as agricultural and open (weather, markets and
  places are the candidates), and who approves each.
- Which data-infra **domain** the data lives in. `schemas/domains.yaml` there has
  no agriculture domain, and adding a domain is a change to that list first.
- The licence for this repository.
