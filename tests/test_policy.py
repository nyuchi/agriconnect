"""The rule, tested the way the other Nyuchi rules are: each test fails if the rule is broken."""

import pytest

from agriconnect.policy import (
    K_MIN,
    OPEN_LICENCES,
    Column,
    Dataset,
    PolicyError,
    check_request,
    eligible,
    problems,
    publishable,
)
from agriconnect.source import build_query


def ds(**over) -> Dataset:
    base = {
        "id": "rain",
        "title": "Rain",
        "domain": "weather",
        "database": "weather",
        "table": "rainfall",
        "licence": "CC-BY-4.0",
        "open": True,
        "enabled": True,
        "approved_by": "owner",
        "min_cell_size": 10,
        "columns": (
            Column("district", "dimension"),
            Column("month", "dimension"),
            Column("rainfall_mm", "measure"),
            Column("station_id", "identifier"),
            Column("farmer_phone", "personal"),
        ),
    }
    base.update(over)
    return Dataset(**base)


def test_a_complete_open_approved_dataset_is_eligible():
    assert eligible(ds())


@pytest.mark.parametrize(
    "over",
    [
        {"open": False},
        {"enabled": False},
        {"approved_by": None},
        {"approved_by": ""},
        {"licence": ""},
        {"licence": "Proprietary"},
        {"licence": "cc-by-4.0"},  # not on the list exactly: fails closed
        {"min_cell_size": K_MIN - 1},
        {"min_cell_size": 0},
    ],
)
def test_each_missing_condition_makes_it_ineligible(over):
    assert not eligible(ds(**over))
    assert problems(ds(**over))


def test_no_measure_or_an_unknown_kind_or_a_bad_name_is_ineligible():
    assert not eligible(ds(columns=(Column("district", "dimension"),)))
    assert not eligible(ds(columns=(*ds().columns, Column("x", "secret"))))
    assert not eligible(ds(table="rainfall; DROP TABLE x"))
    assert not eligible(ds(columns=(*ds().columns, Column("Bad-Name", "dimension"))))


def test_the_licence_allowlist_is_small_and_explicit():
    # CC BY 4.0 is the platform's open-data licence (standards register cc_by_4).
    assert OPEN_LICENCES == frozenset({"CC-BY-4.0"})
    assert "Proprietary" not in OPEN_LICENCES and "" not in OPEN_LICENCES


def test_identifier_and_personal_columns_can_never_be_asked_for():
    for private in ("station_id", "farmer_phone"):
        with pytest.raises(PolicyError):
            check_request(ds(), [private], "rainfall_mm")
        with pytest.raises(PolicyError):
            check_request(ds(), ["district"], private)


def test_undeclared_columns_and_bad_shapes_are_refused():
    with pytest.raises(PolicyError):
        check_request(ds(), ["not_a_column"], "rainfall_mm")
    with pytest.raises(PolicyError):
        check_request(ds(), [], "rainfall_mm")
    with pytest.raises(PolicyError):
        check_request(ds(), ["district", "district"], "rainfall_mm")
    with pytest.raises(PolicyError):
        check_request(ds(), ["district"], "district")  # a dimension is not a measure
    with pytest.raises(PolicyError):
        check_request(ds(enabled=False), ["district"], "rainfall_mm")


def test_small_cells_are_dropped_whatever_the_source_returned():
    rows = [{"district": "a", "n": 9}, {"district": "b", "n": 10}, {"district": "c", "n": 400}]
    assert [r["district"] for r in publishable(ds(), rows)] == ["b", "c"]
    # A catalogue entry that asks for more gets more, and a lower ask cannot go under the floor.
    assert [r["district"] for r in publishable(ds(min_cell_size=50), rows)] == ["c"]
    assert publishable(ds(min_cell_size=1), [{"n": 3}]) == []
    # A row with no count is not an aggregate and is not published.
    assert publishable(ds(), [{"district": "x"}, {"n": "99"}]) == []


def test_the_query_groups_and_floors_and_never_selects_a_private_column():
    sql = build_query(ds(), ["district", "month"], "rainfall_mm", 50)
    assert "GROUP BY `district`, `month`" in sql
    assert "HAVING COUNT(*) >= 10" in sql
    assert "LIMIT 50" in sql
    assert "station_id" not in sql and "farmer_phone" not in sql
    assert "SELECT *" not in sql


def test_the_query_refuses_what_the_policy_refuses():
    with pytest.raises(PolicyError):
        build_query(ds(), ["station_id"], "rainfall_mm", 10)
