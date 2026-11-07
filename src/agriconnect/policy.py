"""
THE RULE: nothing leaves AgriConnect unless it is open, aggregated and checked.

A dataset is served only when every one of these holds. Each is checked here,
in code, and again on every response, because a rule that only the catalogue
file states is a comment, not a control:

- it is `open`, with a licence on the allowlist (unlisted is not open);
- someone named has approved it (`approved_by`) and it is `enabled`;
- every column is declared with a kind. Identifier and personal columns (a
  person, a farm, a phone number, a precise location) may exist in the source
  table but are never selected, grouped or returned: a caller can ask only for
  declared dimensions and measures;
- every row served is an aggregate of at least `min_cell_size` records, and
  never fewer than K_MIN, so a small cell cannot point at one farm.

The allowlist fails closed, as `provenance.ts` does in shamwari-ai/shamwari:
a licence nobody has reviewed is treated as not open.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: The smallest cell any dataset may publish. A catalogue entry can ask for more.
#: Matches the k of the open-data commons (OPEN_DATA_K_ANONYMITY, default 10 in
#: nyuchi-api), published per dataset as bundu:kAnonymity (vocab.bundu.org).
K_MIN = 10

#: The platform's open-data licence is CC BY 4.0 (standards register `cc_by_4`,
#: the licence on the /v1/open-data commons in nyuchi-api). Add another only in
#: a reviewed change that also adds it to the register.
OPEN_LICENCES = frozenset({"CC-BY-4.0"})

KINDS = frozenset({"dimension", "measure", "identifier", "personal"})
EXPOSABLE = frozenset({"dimension", "measure"})

_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class PolicyError(ValueError):
    """The request or the catalogue entry breaks the rule."""


@dataclass(frozen=True)
class Column:
    name: str
    kind: str


@dataclass(frozen=True)
class Dataset:
    id: str
    title: str
    #: The data-infra domain the data belongs to (nyuchi/data-infra schemas/domains.yaml).
    domain: str
    database: str
    table: str
    licence: str
    open: bool
    enabled: bool
    approved_by: str | None
    min_cell_size: int
    columns: tuple[Column, ...] = field(default_factory=tuple)

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


def valid_name(name: str) -> bool:
    return bool(_NAME.match(name))


def problems(d: Dataset) -> list[str]:
    """Everything wrong with a dataset. Empty means it may be served."""
    out: list[str] = []
    if not d.open:
        out.append("not marked open")
    if d.licence not in OPEN_LICENCES:
        out.append(f"licence {d.licence!r} is not on the open allowlist")
    if not d.enabled:
        out.append("not enabled")
    if not d.approved_by:
        out.append("no one has approved it")
    if d.min_cell_size < K_MIN:
        out.append(f"min_cell_size {d.min_cell_size} is below the floor of {K_MIN}")
    for name in (d.database, d.table, *(c.name for c in d.columns)):
        if not valid_name(name):
            out.append(f"name {name!r} is not a plain lowercase identifier")
    for c in d.columns:
        if c.kind not in KINDS:
            out.append(f"column {c.name!r} has unknown kind {c.kind!r}")
    if not any(c.kind == "measure" for c in d.columns):
        out.append("no measure column")
    return out


def eligible(d: Dataset) -> bool:
    return not problems(d)


def check_request(d: Dataset, dims: list[str], measure: str) -> None:
    """Refuse anything but declared dimensions and one declared measure."""
    if not eligible(d):
        raise PolicyError("dataset is not eligible to be served")
    if not dims or len(dims) > 4 or len(set(dims)) != len(dims):
        raise PolicyError("ask for one to four distinct dimensions")
    for name in dims:
        col = d.column(name)
        if col is None or col.kind != "dimension":
            raise PolicyError(f"{name!r} is not a dimension of this dataset")
    col = d.column(measure)
    if col is None or col.kind != "measure":
        raise PolicyError(f"{measure!r} is not a measure of this dataset")


def publishable(d: Dataset, rows: list[dict]) -> list[dict]:
    """Drop every row smaller than the cell floor, whatever the source returned.

    The query asks for this too (HAVING), so a correct source never trips it.
    This is the second check: a source that ignores the query still cannot
    publish a small cell.
    """
    floor = max(d.min_cell_size, K_MIN)
    return [r for r in rows if isinstance(r.get("n"), int) and r["n"] >= floor]
