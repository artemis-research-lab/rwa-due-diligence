"""Test group 4: source ledger."""

import json

import pytest

from test_support import FIXTURES, build_run, clock_at, clock_from_ts, load_fixture, source_fields
from lib import ledger, runstate


def _init(tmp_path):
    runstate.init(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at())
    return runstate.open_project(tmp_path, "acme")


def test_ids_increment_and_clock_is_injected(tmp_path):
    project = _init(tmp_path)
    srcs = load_fixture()["sources"]
    a = runstate.add_source(tmp_path, "acme", clock=clock_from_ts("2026-01-02T03:04:05Z"), **source_fields(srcs[0]))
    b = runstate.add_source(tmp_path, "acme", clock=clock_from_ts("2026-01-02T03:04:06Z"), **source_fields(srcs[1]))
    assert (a["id"], b["id"]) == ("S1", "S2")
    assert (a["retrieved_at"], b["retrieved_at"]) == ("2026-01-02T03:04:05Z", "2026-01-02T03:04:06Z")
    assert a["excerpt_sha256"] == ledger.excerpt_sha256(srcs[0]["excerpt"])
    assert [s["id"] for s in ledger.read_ledger(project.ledger_file)] == ["S1", "S2"]
    assert runstate.load_work(project)["sources"] == [a, b]


def test_offline_gives_null_and_fetch_offline(tmp_path):
    _init(tmp_path)
    fields = dict(source_fields(load_fixture()["sources"][0]), offline=True, fetch="ok")
    src = runstate.add_source(tmp_path, "acme", clock=clock_at(), **fields)
    assert src["retrieved_at"] is None and src["fetch"] == "offline"


def test_fixture_ledger_bytes_reproduced(tmp_path):
    project = build_run(tmp_path)
    assert project.ledger_file.read_bytes() == (FIXTURES / "acme.sources.jsonl").read_bytes()


def test_editing_a_source_in_work_doc_fails_validation(tmp_path):
    project = build_run(tmp_path)
    doc = runstate.load_work(project)
    doc["sources"][1]["title"] = "Edited by hand"
    runstate.save_work(project, doc)
    assert runstate.check(tmp_path, "acme") == [
        "sources[1]: differs from ledger entry 2 (sources must be added with add-source)"]


def test_adding_a_source_by_hand_fails_validation(tmp_path):
    project = build_run(tmp_path)
    doc = runstate.load_work(project)
    extra = dict(doc["sources"][0], id="S9")
    doc["sources"].append(extra)
    runstate.save_work(project, doc)
    assert "sources: 9 entries but the ledger has 8 (sources must be added with add-source)" in \
        runstate.check(tmp_path, "acme")


def test_ledger_is_append_only(tmp_path):
    project = _init(tmp_path)
    srcs = load_fixture()["sources"]
    runstate.add_source(tmp_path, "acme", clock=clock_at(), **source_fields(srcs[0]))
    before = project.ledger_file.read_bytes()
    runstate.add_source(tmp_path, "acme", clock=clock_at(), **source_fields(srcs[1]))
    after = project.ledger_file.read_bytes()
    assert after.startswith(before) and len(after) > len(before)
    assert json.loads(after.decode().splitlines()[-1])["id"] == "S2"


def test_invalid_source_is_rejected_and_not_written(tmp_path):
    project = _init(tmp_path)
    fields = dict(source_fields(load_fixture()["sources"][0]), excerpt="x" * 301)
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.add_source(tmp_path, "acme", clock=clock_at(), **fields)
    assert exc.value.errors == ["excerpt: longer than 300 characters"]
    assert project.ledger_file.read_bytes() == b""
