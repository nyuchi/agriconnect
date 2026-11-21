"""The dataset catalogue: catalogue/datasets.yaml, parsed and held to the policy."""

from __future__ import annotations

from pathlib import Path

import yaml

from .policy import Column, Dataset

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "catalogue" / "datasets.yaml"


def load(path: Path = DEFAULT_PATH) -> dict[str, Dataset]:
    raw = yaml.safe_load(path.read_text()) or {}
    out: dict[str, Dataset] = {}
    for item in raw.get("datasets", []):
        d = Dataset(
            id=str(item["id"]),
            title=str(item.get("title", item["id"])),
            domain=str(item["domain"]),
            database=str(item["database"]),
            table=str(item["table"]),
            licence=str(item.get("licence", "")),
            open=item.get("open") is True,
            enabled=item.get("enabled") is True,
            approved_by=item.get("approved_by") or None,
            min_cell_size=int(item.get("min_cell_size", 0)),
            columns=tuple(Column(str(c["name"]), str(c["kind"])) for c in item.get("columns", [])),
        )
        if d.id in out:
            raise ValueError(f"duplicate dataset id {d.id!r}")
        out[d.id] = d
    return out
