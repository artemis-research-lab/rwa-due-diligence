"""v0.7.0 section 7.2: change log against the migrated earlier record (lib/changes.py)."""

import copy

import pytest

from test_support import build_run, load_fixture, load_v21
from lib import changes, migrate, runstate


def _rows():
    doc = load_fixture()
    return changes.diff(migrate.migrate_to_current(load_v21(), doc["run"]), doc)


def _seeded(doc):
    """doc as a run seeded from it starts: every finding carried from its own id."""
    new = copy.deepcopy(doc)
    for f in new["findings"]:
        f["carried_from"] = f["id"]
    return new


def _row(rows, ref, path):
    found = [r for r in rows if (r["ref"], r["path"]) == (ref, path)]
    assert len(found) == 1, (ref, path)
    return found[0]


def test_no_earlier_record_and_no_change():
    doc = load_fixture()
    assert changes.diff(None, doc) == []
    assert changes.diff(doc, _seeded(doc)) == []
    # The migration itself is never a change: the earlier record is migrated first.
    old = load_v21()
    assert changes.diff(migrate.migrate_to_current(old, doc["run"]), migrate.migrate_to_current(old, doc["run"])) == []


def test_empty_when_not_seeded(tmp_path):
    project = build_run(tmp_path)
    assert runstate.load_work(project)["run"]["seeded_from"] is None
    assert runstate.change_log(project, runstate.load_work(project)) == []


def test_changed_amounts():
    rows = _rows()
    assert _row(rows, "X2", "amounts[0].basis") == {"ref": "X2", "path": "amounts[0].basis", "change": "changed",
                                                    "before": "OTHER", "after": "CURRENT_BALANCE",
                                                    "evidence_added": []}
    assert _row(rows, "X2", "amounts[0].value") == {
        "ref": "X2", "path": "amounts[0].value", "change": "changed", "before": "25000000 [self_reported]",
        "after": "25000000 [verified] (evidence, subject, note changed)", "evidence_added": ["S4"]}
    assert _row(rows, "X2", "amounts[1].value")["change"] == "added"
    assert _row(rows, "X2", "amounts[1].basis")["after"] == "POSITION_VALUE"
    assert _row(rows, "X9", "amounts[0].scope")["before"] == "unchecked (migrated from rwa-dd/2.1)"
    assert _row(rows, "X2", "supply_concentration.ratio")["after"] == "0.5 [verified]"


def test_retyped_finding_via_carried_from():
    rows = _rows()
    assert _row(rows, "G3 -> R1", "type") == {"ref": "G3 -> R1", "path": "type", "change": "changed",
                                              "before": "gap", "after": "unreconciled_transaction",
                                              "evidence_added": []}
    assert _row(rows, "G3", "") == {"ref": "G3", "path": "", "change": "added", "before": None,
                                    "after": "The security agreement over the leased equipment is not public.",
                                    "evidence_added": []}
    assert _row(rows, "D2", "resolution.status")["after"] == "resolved"
    assert not any(r["path"] == "assertions" for r in rows)  # entries are listed, not the empty list


def test_added_source_only():
    rows = _rows()
    assert _row(rows, "S9", "") == {"ref": "S9", "path": "", "change": "added", "before": None,
                                    "after": "Agreed-upon procedures report on the Acme Credit Fund loan sample",
                                    "evidence_added": []}
    assert [r["ref"] for r in rows if r["ref"].startswith("S")] == ["S9"]


def test_rows_sorted_ignored_paths_and_clipped():
    rows = _rows()
    refs = [r["ref"] for r in rows]
    assert refs.index("X9") < refs.index("X10") < refs.index("X13")
    assert rows == sorted(rows, key=lambda r: (changes._natural(r["ref"]), changes._natural(r["path"])))
    assert not any(r["ref"] in ("run", "next_searches") for r in rows)
    assert all(len(r["before"] or "") <= 80 and len(r["after"] or "") <= 120 for r in rows)


def test_objects_added_and_removed():
    old = load_fixture()
    doc = _seeded(old)
    doc["supports"] = []
    rows = changes.diff(old, doc)
    assert rows == [{"ref": "Z1", "path": "", "change": "removed", "before": None, "after": None,
                     "evidence_added": []}]
    rows = changes.diff(doc, _seeded(old))
    assert [(r["ref"], r["change"]) for r in rows] == [("Z1", "added")]
    old = _seeded(old)
    removed = copy.deepcopy(old)
    removed["findings"] = [f for f in removed["findings"] if f["id"] != "C1"]
    assert [(r["ref"], r["change"]) for r in changes.diff(old, removed)] == [("C1", "removed")]


# --------------------------------------------------------------------------- v0.7.5 match="id"

def _legacy_carried():
    """A final version whose findings keep legacy carried_from values that differ from their ids (the fixture
    already has R1 carried_from G3 and G3 carried_from none)."""
    doc = load_fixture()
    for f in doc["findings"]:
        f["carried_from"] = {"D1": "D2", "D2": None, "U1": "D1"}.get(f["id"], f["carried_from"])
    return doc


def test_match_id_between_versions_of_one_run():
    old = _legacy_carried()
    assert changes.diff(old, copy.deepcopy(old), match="id") == []
    # Paired by carried_from, the same unchanged pair gives the spurious rows the seeded log default would show.
    spurious = changes.diff(old, copy.deepcopy(old))
    assert _row(spurious, "D1 -> U1", "type") == {"ref": "D1 -> U1", "path": "type", "change": "changed",
                                                  "before": "discrepancy", "after": "scope_unresolved",
                                                  "evidence_added": []}
    assert _row(spurious, "D2", "")["change"] == "added" and _row(spurious, "U1", "")["change"] == "removed"


def test_match_id_shows_a_real_finding_change_once():
    old = _legacy_carried()
    new = copy.deepcopy(old)
    finding = [f for f in new["findings"] if f["id"] == "U1"][0]
    finding["type"] = "gap"
    finding["statement"] = "Scope now checked."
    rows = changes.diff(old, new, match="id")
    assert [(r["ref"], r["path"], r["change"]) for r in rows] == [("U1", "statement", "changed"),
                                                                 ("U1", "type", "changed")]
    assert _row(rows, "U1", "type")["after"] == "gap"
    new["findings"] = [f for f in new["findings"] if f["id"] != "C1"]
    assert ("C1", "", "removed") in [(r["ref"], r["path"], r["change"]) for r in changes.diff(old, new, match="id")]
    new["findings"][0]["carried_from"] = "C1"  # compared like any other leaf
    assert _row(changes.diff(old, new, match="id"), "G1", "carried_from")["after"] == "C1"


def test_match_must_be_known():
    with pytest.raises(ValueError):
        changes.diff(load_fixture(), load_fixture(), match="statement")
