"""Where the rows come from: Apache Doris on the Nyuchi data layer, over its MySQL wire."""

from __future__ import annotations

import os
from typing import Protocol

from .policy import Dataset, check_request, valid_name


class Source(Protocol):
    def aggregate(self, d: Dataset, dims: list[str], measure: str, limit: int) -> list[dict]: ...


def build_query(d: Dataset, dims: list[str], measure: str, limit: int) -> str:
    """One aggregate query. Names are checked against the catalogue and the plain
    identifier pattern before they are put in the text; values are never in it."""
    check_request(d, dims, measure)
    for name in (d.database, d.table, measure, *dims):
        if not valid_name(name):  # belt and braces: check_request already holds this
            raise ValueError("bad identifier")
    cols = ", ".join(f"`{c}`" for c in dims)
    return (
        f"SELECT {cols}, COUNT(*) AS n, AVG(`{measure}`) AS mean "
        f"FROM `{d.database}`.`{d.table}` "
        f"GROUP BY {cols} HAVING COUNT(*) >= {int(d.min_cell_size)} "
        f"ORDER BY {cols} LIMIT {int(min(max(limit, 1), 1000))}"
    )


class DorisSource:
    """A read-only login on the Doris of nyuchi/data-infra, over Fly's private network.

    It connects when it is first used, never at import, so the tests and the
    app start with no database. The login must be a role that can only SELECT
    from the domain's database; AgriConnect never writes.
    """

    def __init__(self) -> None:
        self._conn = None

    def _connect(self):
        import pymysql

        return pymysql.connect(
            host=os.environ["DORIS_HOST"],
            port=int(os.environ.get("DORIS_PORT", "9030")),
            user=os.environ["DORIS_USER"],
            password=os.environ["DORIS_PASSWORD"],
            read_timeout=20,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def aggregate(self, d: Dataset, dims: list[str], measure: str, limit: int) -> list[dict]:
        sql = build_query(d, dims, measure, limit)
        if self._conn is None:
            self._conn = self._connect()
        with self._conn.cursor() as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
