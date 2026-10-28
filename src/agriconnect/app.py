"""AgriConnect's API. Internal only: no public address, one bearer token."""

from __future__ import annotations

import hmac
import os
from collections.abc import Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from . import catalogue
from .policy import Dataset, PolicyError, eligible, publishable
from .source import DorisSource, Source


def create_app(
    datasets: dict[str, Dataset] | None = None,
    source: Source | None = None,
    token: Callable[[], str | None] = lambda: os.environ.get("AGRICONNECT_TOKEN"),
) -> FastAPI:
    catalog = datasets if datasets is not None else catalogue.load()
    src: Source = source if source is not None else DorisSource()
    app = FastAPI(title="AgriConnect", docs_url=None, redoc_url=None)

    def caller(authorization: str | None = Header(default=None)) -> None:
        expected = token()
        # Fail closed: a service with no token configured answers nothing.
        if not expected:
            raise HTTPException(503, "not_configured")
        given = (authorization or "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(given.encode(), expected.encode()):
            raise HTTPException(401, "invalid_token")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "service": "agriconnect"}

    @app.get("/v1/datasets", dependencies=[Depends(caller)])
    def list_datasets() -> dict:
        return {
            "datasets": [
                {
                    "id": d.id,
                    "title": d.title,
                    "licence": d.licence,
                    "min_cell_size": d.min_cell_size,
                    "dimensions": [c.name for c in d.columns if c.kind == "dimension"],
                    "measures": [c.name for c in d.columns if c.kind == "measure"],
                }
                for d in catalog.values()
                if eligible(d)
            ]
        }

    @app.get("/v1/datasets/{dataset_id}/series", dependencies=[Depends(caller)])
    def series(
        dataset_id: str,
        dims: str = Query(min_length=1, max_length=200),
        measure: str = Query(min_length=1, max_length=64),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> dict:
        d = catalog.get(dataset_id)
        # An ineligible dataset is indistinguishable from one that does not exist.
        if d is None or not eligible(d):
            raise HTTPException(404, "not_found")
        wanted = [x.strip() for x in dims.split(",") if x.strip()]
        try:
            from .policy import check_request

            check_request(d, wanted, measure)
        except PolicyError as e:
            raise HTTPException(400, str(e)) from e
        rows = publishable(d, src.aggregate(d, wanted, measure, limit))
        return {
            "dataset": d.id,
            "licence": d.licence,
            "min_cell_size": d.min_cell_size,
            "dimensions": wanted,
            "measure": measure,
            "rows": rows,
        }

    return app


def app() -> FastAPI:  # uvicorn --factory agriconnect.app:app
    return create_app()
