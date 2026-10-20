"""v0.7.0 section 7.2: change log against the migrated earlier record (lib/changes.py)."""

import copy

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
