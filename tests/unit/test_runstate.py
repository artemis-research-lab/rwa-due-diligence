"""Test groups 5 (path safety) and 6 (state machine)."""

import os

import pytest

import hashlib
import json

from test_support import FIXTURES, GOLDEN, build_run, clock_at, load_v1, load_v21, walk
from lib import flow, migrate, runstate, schema
from lib.textutil import dump_json

# finalize requires d2 v0.9.0 since P3; these tests run only where it is on PATH (see test_flow.py).
NEEDS_D2 = pytest.mark.skipif(flow.find_d2() is None, reason="d2 %s not on PATH" % flow.D2_VERSION)
FLOW_KEYS = ("T1-settlement", "T1-claim", "T1-repayment", "T2-settlement")


def _to_awaiting(tmp_path):
    project = build_run(tmp_path)
    runstate.make_review(tmp_path, "acme")
    return project


def _directives(tmp_path, project, text, name="reply.txt"):
    path = project.scratch / "logs" / name
    path.write_bytes(text.encode("utf-8"))
    return runstate.apply_directives(tmp_path, "acme", path)


# --------------------------------------------------------------------------- path safety

@pytest.mark.parametrize("slug", ["../x", "A", "x", "a/b", "-ab", "a" * 42, ""])
def test_bad_slugs_rejected(tmp_path, slug):
    with pytest.raises(runstate.ContractError):
        runstate.init(tmp_path, slug, "https://a.example/", clock=clock_at())
    assert walk(tmp_path) == []


def test_good_slug_accepted(tmp_path):
    runstate.init(tmp_path, "ab", "https://a.example/", clock=clock_at())
    assert (tmp_path / "ab" / "audit" / "state.json").is_file()


def test_path_escaping_project_dir_raises(tmp_path):
    project = runstate.Project(tmp_path, "acme")
    with pytest.raises(runstate.ContractError):
        project.safe(project.dir / ".." / "elsewhere.txt")
    with pytest.raises(runstate.ContractError):
        project.write_text(tmp_path / "outside.txt", "x")
    assert not (tmp_path / "outside.txt").exists()


def test_symlink_escaping_project_dir_raises(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    project = build_run(tmp_path / "reports")
    os.rename(project.rounds, tmp_path / "old-rounds")
    try:
        os.symlink(outside, project.rounds, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported here")
    with pytest.raises(runstate.ContractError):
        runstate.make_review(tmp_path / "reports", "acme")
    assert list(outside.iterdir()) == []


def test_symlinked_project_dir_raises(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "reports").mkdir()
    try:
        os.symlink(target, tmp_path / "reports" / "acme", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported here")
    with pytest.raises(runstate.ContractError):
        runstate.init(tmp_path / "reports", "acme", "https://a.example/", clock=clock_at())


# --------------------------------------------------------------------------- state machine

def test_init_layout_and_state(tmp_path):
    out = runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    assert out["run_id"] == "acme-20261001T080000Z"
    project = runstate.open_project(tmp_path, "acme")
    assert runstate.load_state(project) == {"slug": "acme", "run_id": "acme-20261001T080000Z", "round": 1,
                                            "phase": "research", "status": "draft"}
    for sub in ("raw", "text", "draft", "logs"):
        assert (project.scratch / sub).is_dir()
    assert project.ledger_file.read_bytes() == b""
    assert not any(p.exists() for p in project.outputs())


def test_skeleton_fails_only_on_flow_and_yield(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    assert runstate.check(tmp_path, "acme") == ["project.products[0]: P1 has no yield entry",
                                                "strategies[0]: T1 has no flow edge with view settlement"]
    doc = runstate.load_work(runstate.open_project(tmp_path, "acme"))
    assert doc["run"]["seeded_from"] is None and doc["run"]["skill_version"] == schema.SKILL_VERSION
    assert [t["component"] for t in doc["strategies"]] == ["CORE_CREDIT"]
    assert [t["products"] for t in doc["strategies"]] == [["P1"]]
    assert [h["product"] for h in doc["holder_rights"]] == ["P1"]


def test_review_refused_on_skeleton(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    with pytest.raises(runstate.InvalidError):
        runstate.make_review(tmp_path, "acme")
    project = runstate.open_project(tmp_path, "acme")
    assert not (project.round_dir(1) / "review.md").exists()
    assert runstate.load_state(project)["phase"] == "research"


def test_directives_refused_when_not_awaiting(tmp_path):
    project = build_run(tmp_path)
    with pytest.raises(runstate.ContractError):
        _directives(tmp_path, project, "accept N1\n")


def test_finalize_refused_before_finalize_directive(tmp_path):
    project = build_run(tmp_path)
    with pytest.raises(runstate.ContractError):
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    runstate.make_review(tmp_path, "acme")
    with pytest.raises(runstate.ContractError):
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    _directives(tmp_path, project, "accept N1\n")
    with pytest.raises(runstate.ContractError):
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert not any(p.exists() for p in project.outputs())


def test_directives_advance_round_and_update_work_doc(tmp_path):
    project = _to_awaiting(tmp_path)
    out = _directives(tmp_path, project, "accept N1 | priority N2,N1\n")
    assert out == {"round": 2, "phase": "research", "commands": 2}
    assert runstate.load_work(project)["run"]["round"] == 2
    assert (project.round_dir(1) / "directives.txt").read_bytes() == b"accept N1 | priority N2,N1\n"
    assert (project.round_dir(1) / "directives.json").is_file()
    assert runstate.check(tmp_path, "acme") == []


@pytest.mark.d2
@NEEDS_D2
def test_full_cycle_and_new_run_archives(tmp_path):
    project = _to_awaiting(tmp_path)
    _directives(tmp_path, project, "finalize\n")
    assert runstate.load_state(project)["phase"] == "ready_to_finalize"
    result = runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert result["rounds"] == 1
    assert all(os.path.isfile(p) for p in result["outputs"])
    state = runstate.load_state(project)
    assert (state["status"], state["phase"]) == ("final", "final")

    with pytest.raises(runstate.ContractError):
        runstate.init(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at())
    with pytest.raises(runstate.ContractError):
        runstate.add_source(tmp_path, "acme", clock=clock_at(), url="u", title="t", source_type="other",
                            origin="analyst", fetch="ok", excerpt="e")

    old_id = state["run_id"]
    later = clock_at(__import__("datetime").datetime(2026, 11, 1, tzinfo=__import__("datetime").timezone.utc))
    out = runstate.init(tmp_path, "acme", "https://acme-yield.example/", clock=later, new_run=True)
    archive = project.archive / old_id
    assert (archive / "acme.dd.json").is_file() and (archive / "acme.report.md").is_file()
    assert (archive / "acme.flow-T1-settlement.svg").is_file() and (archive / "acme.flow-T2-settlement.svg").is_file()
    assert (archive / "audit" / "state.json").is_file()
    assert not any(p.exists() for p in project.outputs())
    assert runstate.load_state(project)["run_id"] == out["run_id"] == "acme-20261101T000000Z"


def test_init_on_draft_refused_without_new_run(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    with pytest.raises(runstate.ContractError) as exc:
        runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    assert str(exc.value) == ('run exists (phase research); use "dd.py status" to inspect or --new-run to archive it'
                              ' and start again')


@pytest.mark.d2
@NEEDS_D2
def test_finalized_document_is_schema_ordered(tmp_path):
    project = _to_awaiting(tmp_path)
    _directives(tmp_path, project, "finalize\n")
    runstate.finalize(tmp_path, "acme", clock=clock_at())
    text = project.output("dd.json").read_bytes().decode("utf-8")
    assert text.endswith("}\n") and not text.endswith("\n\n")
    assert text.startswith('{\n  "schema_version": "rwa-dd/2.2",\n  "run": {\n    "run_id"')
    assert '"finalized_at": "2026-10-01T08:00:00Z"' in text


def test_render_draft_any_phase(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    out = runstate.render_draft(tmp_path, "acme")
    assert out["outputs"][0].endswith(os.path.join(".scratch", "draft", "acme.report.md"))
    assert open(out["outputs"][0], encoding="utf-8").read().startswith("# RWA Due Diligence: acme\n")
    assert not any(p.endswith(".html") for p in out["outputs"])


# --------------------------------------------------------------------------- P3 figures pipeline

def _ready(tmp_path):
    project = _to_awaiting(tmp_path)
    _directives(tmp_path, project, "finalize\n")
    return project


def test_finalize_without_d2_writes_nothing(tmp_path, monkeypatch):
    project = _ready(tmp_path)
    before = walk(project.dir)
    monkeypatch.setattr(flow, "find_d2", lambda: None)
    with pytest.raises(flow.DependencyError) as exc:
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert str(exc.value) == "d2 v0.9.0 required, found none on PATH"
    assert walk(project.dir) == before
    assert not any(p.exists() for p in project.outputs())
    assert runstate.load_state(project)["phase"] == "ready_to_finalize"


def test_finalize_with_wrong_d2_writes_nothing(tmp_path, monkeypatch):
    project = _ready(tmp_path)
    before = walk(project.dir)
    monkeypatch.setattr(flow, "find_d2", lambda: "d2-fake")

    def wrong(path):
        raise flow.DependencyError("d2 v0.9.0 required, found v0.8.0")
    monkeypatch.setattr(flow, "check_d2", wrong)
    with pytest.raises(flow.DependencyError):
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert walk(project.dir) == before
    assert runstate.load_state(project)["phase"] == "ready_to_finalize"


def test_render_draft_without_d2_warns_and_omits_figures(tmp_path, monkeypatch):
    build_run(tmp_path)
    monkeypatch.setattr(flow, "find_d2", lambda: None)
    out = runstate.render_draft(tmp_path, "acme")
    assert out["warnings"] == ["d2 v0.9.0 not found: diagrams omitted"]
    assert [os.path.basename(p) for p in out["outputs"]] == ["acme.report.md", "acme.derived.json"]
    assert "![Fund flow" not in open(out["outputs"][0], encoding="utf-8").read()


@pytest.mark.d2
@NEEDS_D2
def test_render_draft_with_d2_writes_svgs(tmp_path):
    project = build_run(tmp_path)
    out = runstate.render_draft(tmp_path, "acme")
    assert "warnings" not in out
    names = [os.path.basename(p) for p in out["outputs"]]
    assert names == ["acme.report.md", "acme.derived.json"] + ["acme.flow-%s.svg" % k for k in FLOW_KEYS]
    assert all(os.path.dirname(p) == str(project.scratch / "draft") for p in out["outputs"])
    assert "![Fund flow T1 claim](acme.flow-T1-claim.svg)" in open(out["outputs"][0], encoding="utf-8").read()


@pytest.mark.d2
@NEEDS_D2
def test_finalize_with_d2_writes_svgs_in_outputs(tmp_path):
    project = _ready(tmp_path)
    result = runstate.finalize(tmp_path, "acme", clock=clock_at())
    names = [os.path.basename(p) for p in result["outputs"]]
    assert names == ["acme.dd.json", "acme.derived.json", "acme.report.md"] + [
        "acme.flow-%s.svg" % k for k in FLOW_KEYS] + ["acme.manifest.json"]
    for key in FLOW_KEYS:
        assert project.flow_output(key).read_bytes() == (GOLDEN / ("acme.flow-%s.svg" % key)).read_bytes()
    md = project.output("report.md").read_bytes().decode("utf-8")
    assert "![Fund flow T1 settlement](acme.flow-T1-settlement.svg)" in md
    assert "![Fund flow T2 settlement](acme.flow-T2-settlement.svg)" in md
    assert [p.name for p in project.outputs()] == names
    assert not any(p.suffix == ".html" for p in project.dir.rglob("*"))


@pytest.mark.d2
@NEEDS_D2
def test_finalize_writes_manifest_last(tmp_path):
    project = _ready(tmp_path)
    result = runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert os.path.basename(result["outputs"][-1]) == "acme.manifest.json"
    manifest = json.loads(project.output("manifest.json").read_bytes().decode("utf-8"))
    hashes = {f["path"]: f["sha256"] for f in manifest["files"]}
    # every listed file, the run state included, already has its final bytes when the manifest is written
    for path, digest in hashes.items():
        assert hashlib.sha256((project.dir / path).read_bytes()).hexdigest() == digest, path
    assert runstate.load_state(project)["phase"] == "final" and "audit/state.json" in hashes
    assert "acme.manifest.json" not in hashes
    assert project.output("manifest.json") in project.outputs()

# --------------------------------------------------------------------------- v0.4.1 amend

AMEND = b"note sUSDai upgrades missed\r\nadd-source https://x.example/safe : Safe history\n"


def _amend_file(project, data=AMEND, name="amend-1.txt"):
    path = project.scratch / "logs" / name
    path.write_bytes(data)
    return path


def _final(tmp_path):
    project = _to_awaiting(tmp_path)
    _directives(tmp_path, project, "finalize\n")
    runstate.finalize(tmp_path, "acme", clock=clock_at())
    return project


def _snapshot(project):
    return walk(project.dir), project.state_file.read_bytes(), project.work_file.read_bytes()


@pytest.mark.parametrize("phase", ["research", "awaiting_directives", "ready_to_finalize"])
def test_amend_requires_final_run(tmp_path, phase):
    project = build_run(tmp_path)
    if phase != "research":
        runstate.make_review(tmp_path, "acme")
    if phase == "ready_to_finalize":
        _directives(tmp_path, project, "finalize\n")
    path = _amend_file(project)
    before = _snapshot(project)
    with pytest.raises(runstate.ContractError) as exc:
        runstate.amend(tmp_path, "acme", path)
    assert str(exc.value) == "amend requires a final run (current phase: %s)" % phase
    assert _snapshot(project) == before


@pytest.mark.d2
@NEEDS_D2
def test_amend_archives_outputs_and_reopens_round(tmp_path):
    project = _final(tmp_path)
    run_id = runstate.load_state(project)["run_id"]
    outputs = [p.name for p in project.outputs()]
    result = runstate.amend(tmp_path, "acme", _amend_file(project))
    archive = project.archive / ("%s.v0" % run_id)
    assert result == {"amendment": 1, "round": 2, "phase": "research", "archived_to": str(archive.resolve()),
                      "commands": 2}
    assert sorted(p.name for p in archive.iterdir()) == sorted(outputs)
    assert "acme.manifest.json" in outputs and (archive / "acme.manifest.json").is_file()
    assert not any(p.exists() for p in project.outputs())
    assert (project.round_dir(2) / "amend.txt").read_bytes() == AMEND
    record = runstate.load_json_text((project.round_dir(2) / "amend.json").read_bytes().decode("utf-8"))
    assert record == {"amendment": 1, "reopens_round": 2, "commands": [
        {"cmd": "note", "text": "sUSDai upgrades missed", "line": 1},
        {"cmd": "add-source", "target": "https://x.example/safe", "why": "Safe history", "line": 2}]}
    run = runstate.load_work(project)["run"]
    assert (run["round"], run["status"], run["finalized_at"]) == (2, "draft", None)
    state = runstate.load_state(project)
    assert (state["round"], state["phase"], state["status"], state["amendment"]) == (2, "research", "draft", 1)
    assert runstate.check(tmp_path, "acme") == []
    assert runstate.status(tmp_path, "acme")["state"]["amendment"] == 1


@pytest.mark.d2
@NEEDS_D2
@pytest.mark.parametrize("data, message", [
    (b"note x\nfinalize\n", "line 2: finalize is not allowed in an amendment"),
    (b"drop D1 : superseded\n", "line 0: an amendment needs at least one note"),
    (b"note \xff\n", "line 0: amendment file is not UTF-8"),
])
def test_amend_invalid_file_changes_nothing(tmp_path, data, message):
    project = _final(tmp_path)
    path = _amend_file(project, data)
    before = _snapshot(project)
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.amend(tmp_path, "acme", path)
    assert exc.value.errors == [message]
    assert _snapshot(project) == before


@pytest.mark.d2
@NEEDS_D2
def test_amend_refuses_existing_archive(tmp_path):
    project = _final(tmp_path)
    (project.archive / ("%s.v0" % runstate.load_state(project)["run_id"])).mkdir(parents=True)
    path = _amend_file(project)
    before = _snapshot(project)
    with pytest.raises(runstate.ContractError, match="already exists"):
        runstate.amend(tmp_path, "acme", path)
    assert _snapshot(project) == before


@pytest.mark.d2
@NEEDS_D2
def test_second_cycle_after_amend(tmp_path):
    project = _final(tmp_path)
    run_id = runstate.load_state(project)["run_id"]
    runstate.amend(tmp_path, "acme", _amend_file(project))
    runstate.make_review(tmp_path, "acme")
    _directives(tmp_path, project, "finalize\n", name="r2.txt")
    result = runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert result["rounds"] == 2 and all(os.path.isfile(p) for p in result["outputs"])
    records = runstate.round_records(project, 2)
    assert [h for h, _ in records] == ["Round 1", "Amendment 1 (reopens round 2)", "Round 2"]
    assert records[1][1] == AMEND.decode("utf-8")
    report = project.output("report.md").read_bytes().decode("utf-8")
    assert "### Amendment 1 (reopens round 2)" in report and "| amendments | 1 |" in report

    second = runstate.amend(tmp_path, "acme", _amend_file(project, b"note again\n", "amend-2.txt"))
    assert (second["amendment"], second["round"]) == (2, 3)
    assert second["archived_to"] == str((project.archive / ("%s.v1" % run_id)).resolve())
    assert (project.archive / ("%s.v1" % run_id) / "acme.dd.json").is_file()


@pytest.mark.d2
@NEEDS_D2
def test_init_on_final_run_points_to_amend(tmp_path):
    _final(tmp_path)
    with pytest.raises(runstate.ContractError) as exc:
        runstate.init(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at())
    assert 'dd.py amend' in str(exc.value)


# --------------------------------------------------------------------------- v0.4.2

@pytest.mark.d2
@NEEDS_D2
def test_final_report_marks_rejected_search(tmp_path):
    project = _to_awaiting(tmp_path)
    _directives(tmp_path, project, "reject N1\nfinalize\n")
    runstate.finalize(tmp_path, "acme", clock=clock_at())
    md = project.output("report.md").read_bytes().decode("utf-8")
    s13 = md[md.index("## Appendix F. All findings"):md.index("## Appendix G. History")]
    assert "**G1** [legal] [MATERIAL] [BLOCKING]" in s13 and "**N" not in s13
    d = md[md.index("## Appendix M. Searches not run"):]
    assert "- **N1** Custody agreement and issuer accounts" in d
    assert "(resolves G1; est 6 calls) -- rejected by the analyst\n" in d
    assert "(resolves G2, D1; est 4 calls) -- not run\n" in d


def test_rejected_ids_reads_only_given_round(tmp_path):
    project = _to_awaiting(tmp_path)
    _directives(tmp_path, project, "reject N2\n")
    assert runstate.rejected_ids(project, 1) == {"N2"}
    assert runstate.rejected_ids(project, 2) == set()


@pytest.mark.d2
@NEEDS_D2
def test_amend_sets_skill_version_and_new_run_keeps_v0(tmp_path):
    project = _final(tmp_path)
    doc = runstate.load_work(project)
    doc["run"]["skill_version"] = "0.4.1"
    runstate.save_work(project, doc)
    run_id = runstate.load_state(project)["run_id"]
    runstate.amend(tmp_path, "acme", _amend_file(project))
    assert runstate.load_work(project)["run"]["skill_version"] == schema.SKILL_VERSION

    later = clock_at(__import__("datetime").datetime(2026, 11, 1, tzinfo=__import__("datetime").timezone.utc))
    runstate.init(tmp_path, "acme", "https://acme-yield.example/", clock=later, new_run=True)
    assert (project.archive / run_id / "audit" / "state.json").is_file()
    assert (project.archive / ("%s.v0" % run_id) / "acme.dd.json").is_file()
    assert (project.archive / ("%s.v0" % run_id) / "acme.report.md").is_file()


def test_runstate_ends_with_single_newline():
    data = (GOLDEN.parents[1] / "lib" / "runstate.py").read_bytes()
    assert data.endswith(b"\n") and not data.endswith(b"\n\n")


# --------------------------------------------------------------------------- v0.5.0 init --seed-from

LATER = __import__("datetime").datetime(2026, 11, 1, tzinfo=__import__("datetime").timezone.utc)


def _final_v1(tmp_path):
    """A final run whose record is the rwa-dd/1.0 fixture and whose outputs have the pre-0.5.0 names."""
    project = _final(tmp_path)
    state = runstate.load_state(project)
    work = runstate.load_work(project)
    old = load_v1()
    old["run"] = {k: work["run"][k] for k in old["run"]}
    old["run"]["skill_version"] = "0.4.2"
    old["sources"] = work["sources"]  # the ledger now also holds S9
    project.work_file.write_bytes(dump_json(old).encode("utf-8"))
    project.output("dd.json").write_bytes(dump_json(old).encode("utf-8"))
    for key in FLOW_KEYS:
        project.flow_output(key).unlink()
    for name in ("report.html", "flow-P1.svg", "flow-P2.svg"):
        project.output(name).write_bytes(b"legacy\n")
    return project, state["run_id"]


@pytest.mark.d2
@NEEDS_D2
def test_seed_from_final_v1_run(tmp_path):
    project, old_id = _final_v1(tmp_path)
    ledger_before = project.ledger_file.read_bytes()
    out = runstate.seed(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at(LATER))
    assert out == {"project_dir": str(project.dir), "run_id": "acme-20261101T000000Z",
                   "work_file": str(project.work_file), "seeded_from": old_id, "sources": 9}
    archive = project.archive / old_id
    assert sorted(p.name for p in archive.iterdir()) == [
        "acme.dd.json", "acme.derived.json", "acme.flow-P1.svg", "acme.flow-P2.svg", "acme.manifest.json",
        "acme.report.html", "acme.report.md", "audit"]
    assert (archive / "audit" / "state.json").is_file()
    assert project.ledger_file.read_bytes() == ledger_before == (archive / "audit" / "sources.jsonl").read_bytes()
    assert not any(p.exists() for p in project.outputs()) and project.legacy_outputs() == []
    doc = runstate.load_work(project)
    assert doc["schema_version"] == "rwa-dd/2.2"
    assert (doc["run"]["seeded_from"], doc["run"]["round"], doc["run"]["status"], doc["run"]["finalized_at"],
            doc["run"]["skill_version"]) == (old_id, 1, "draft", None, schema.SKILL_VERSION)
    assert runstate.check(tmp_path, "acme") == []
    assert runstate.load_state(project) == {"slug": "acme", "run_id": "acme-20261101T000000Z", "round": 1,
                                            "phase": "research", "status": "draft"}
    assert (project.scratch / "raw").is_dir()


def test_seed_from_2_2_run_empties_next_searches(tmp_path):
    project = build_run(tmp_path)
    old_id = runstate.load_state(project)["run_id"]
    before = runstate.load_work(project)
    out = runstate.seed(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at(LATER))
    assert out["seeded_from"] == old_id and out["sources"] == 9
    doc = runstate.load_work(project)
    assert doc["next_searches"] == [] and before["next_searches"]
    assert doc["interfaces"] == before["interfaces"]
    assert [dict(f, carried_from=None) for f in doc["findings"]] == \
        [dict(f, carried_from=None) for f in before["findings"]]
    assert [f["carried_from"] for f in doc["findings"]] == [f["id"] for f in doc["findings"]]
    assert doc["run"]["seeded_from"] == old_id and doc["run"]["started_at"] == "2026-11-01T00:00:00Z"
    assert runstate.check(tmp_path, "acme") == []
    assert (project.archive / old_id / "audit" / "dd.work.json").is_file()


def test_seed_without_run_refused(tmp_path):
    with pytest.raises(runstate.ContractError, match="to seed from"):
        runstate.seed(tmp_path, "acme", "https://a.example/", clock=clock_at())
    assert walk(tmp_path) == []


def test_seed_unknown_version_refused_before_archiving(tmp_path):
    project = build_run(tmp_path)
    doc = runstate.load_work(project)
    doc["schema_version"] = "rwa-dd/0.9"
    project.work_file.write_bytes(dump_json(doc).encode("utf-8"))
    before = _snapshot(project)
    with pytest.raises(runstate.ContractError, match="cannot seed from schema version"):
        runstate.seed(tmp_path, "acme", "https://a.example/", clock=clock_at(LATER))
    assert _snapshot(project) == before


def test_seed_invalid_result_restores_archive(tmp_path, monkeypatch):
    project = build_run(tmp_path)
    doc = runstate.load_work(project)
    old = load_v1()
    old["run"] = {k: doc["run"][k] for k in old["run"]}
    old["sources"] = doc["sources"]
    project.work_file.write_bytes(dump_json(old).encode("utf-8"))
    (project.dir / "acme.report.html").write_bytes(b"legacy\n")
    before = _snapshot(project)
    monkeypatch.setattr(migrate, "migrate_to_current",
                        lambda old, run: dict(old, run=run, schema_version=schema.SCHEMA_VERSION))
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.seed(tmp_path, "acme", "https://a.example/", clock=clock_at(LATER))
    assert any("unknown key" in e or "missing key" in e for e in exc.value.errors)
    assert _snapshot(project) == before
    assert not project.archive.exists() or list(project.archive.iterdir()) == []


# --------------------------------------------------------------------------- v0.6.0 seeding 2.0, finalize checks

def _final_v2(tmp_path):
    """A final run whose record is the rwa-dd/2.0 fixture (same ledger), with v0.5.x outputs in place."""
    project = _final(tmp_path)
    state = runstate.load_state(project)
    work = runstate.load_work(project)
    old = json.loads((FIXTURES / "acme_v2.dd.json").read_bytes().decode("utf-8"))
    old["run"] = dict(work["run"], skill_version="0.5.0")
    old["sources"] = work["sources"]
    project.work_file.write_bytes(dump_json(old).encode("utf-8"))
    project.output("dd.json").write_bytes(dump_json(old).encode("utf-8"))
    return project, state["run_id"], old


@pytest.mark.d2
@NEEDS_D2
def test_seed_from_final_v2_run(tmp_path):
    project, old_id, old = _final_v2(tmp_path)
    ledger_before = project.ledger_file.read_bytes()
    outputs_before = sorted(p.name for p in project.outputs())
    out = runstate.seed(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at(LATER))
    assert out == {"project_dir": str(project.dir), "run_id": "acme-20261101T000000Z",
                   "work_file": str(project.work_file), "seeded_from": old_id, "sources": 9}
    archive = project.archive / old_id
    assert sorted(p.name for p in archive.iterdir()) == sorted(outputs_before + ["audit"])
    assert project.ledger_file.read_bytes() == ledger_before == (archive / "audit" / "sources.jsonl").read_bytes()
    doc = runstate.load_work(project)
    assert doc == migrate.migrate_to_current(old, doc["run"])
    assert (doc["schema_version"], doc["run"]["seeded_from"], doc["run"]["skill_version"]) == \
        ("rwa-dd/2.2", old_id, schema.SKILL_VERSION)
    assert [f["scope_note"] for f in doc["findings"] if f["type"] == "discrepancy"] == \
        [schema.MIGRATED_NOTE_21] * 2
    assert runstate.check(tmp_path, "acme") == []


def _seeded_v2_ready(tmp_path):
    project, _, _ = _final_v2(tmp_path)
    runstate.seed(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at(LATER))
    runstate.make_review(tmp_path, "acme")
    review = (project.round_dir(1) / "review.md").read_bytes().decode("utf-8")
    pending = review[review.index("## Migration checks pending"):review.index("## Material findings")]
    assert "**D1**" in pending and "**D2**" in pending
    _directives(tmp_path, project, "finalize\n", name="seeded.txt")
    return project


@pytest.mark.d2
@NEEDS_D2
def test_finalize_refuses_migration_placeholder_then_succeeds(tmp_path):
    project = _seeded_v2_ready(tmp_path)
    before = _snapshot(project)
    with pytest.raises(runstate.ContractError) as exc:
        runstate.finalize(tmp_path, "acme", clock=clock_at(LATER))
    assert str(exc.value) == "D1: scope not checked (scope_note is a migration placeholder)"
    assert _snapshot(project) == before
    doc = runstate.load_work(project)
    doc["findings"][3].update({"scope_note": "Both state the P2 vault fee.", "scope_match": "matched",
                               "subjects": ["X6.terms"], "assertions": [
                                   {"source": "S7", "statement": "Fee 0.30 percent.", "as_of": "2026-03-15"},
                                   {"source": "S1", "statement": "No fee.", "as_of": None}]})
    runstate.save_work(project, doc)
    with pytest.raises(runstate.ContractError, match="^D2: scope not checked"):
        runstate.finalize(tmp_path, "acme", clock=clock_at(LATER))
    doc["findings"][4].update({"scope_note": "Both describe the X4 security.", "scope_match": "matched",
                               "assertions": [{"source": "S8", "statement": "Secured.", "as_of": None},
                                              {"source": "S5", "statement": "Unsecured.", "as_of": None}]})
    runstate.save_work(project, doc)
    result = runstate.finalize(tmp_path, "acme", clock=clock_at(LATER))
    assert all(os.path.isfile(p) for p in result["outputs"])
    final = runstate.load_work(project)
    assert final["run"]["status"] == "final" and final["run"]["skill_version"] == schema.SKILL_VERSION


@pytest.mark.d2
@NEEDS_D2
def test_finalize_sets_skill_version(tmp_path):
    project = _to_awaiting(tmp_path)
    doc = runstate.load_work(project)
    doc["run"]["skill_version"] = "0.5.0"
    runstate.save_work(project, doc)
    _directives(tmp_path, project, "finalize\n")
    runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert runstate.load_work(project)["run"]["skill_version"] == schema.SKILL_VERSION
    final = json.loads(project.output("dd.json").read_bytes().decode("utf-8"))
    assert final["run"]["skill_version"] == schema.SKILL_VERSION


def test_finalize_refusal_needs_no_d2(tmp_path, monkeypatch):
    project = _to_awaiting(tmp_path)
    doc = runstate.load_work(project)
    doc["findings"][4]["scope_note"] = schema.MIGRATED_SCOPE_NOTE
    runstate.save_work(project, doc)
    _directives(tmp_path, project, "finalize\n")
    monkeypatch.setattr(flow, "find_d2", lambda: None)
    with pytest.raises(runstate.ContractError, match="^D2: scope not checked"):
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert runstate.load_state(project)["phase"] == "ready_to_finalize"


def test_seed_version_accepts_four_versions():
    for version in ("rwa-dd/1.0", "rwa-dd/2.0", "rwa-dd/2.1", "rwa-dd/2.2"):
        assert runstate._seed_version({"schema_version": version}) == version
    with pytest.raises(runstate.ContractError) as exc:
        runstate._seed_version({"schema_version": "rwa-dd/0.9"})
    assert "supported: rwa-dd/1.0, rwa-dd/2.0, rwa-dd/2.1, rwa-dd/2.2" in str(exc.value)


# --------------------------------------------------------------------------- v0.7.0 section 4.2

def _final_v21(tmp_path):
    """A final run whose record is the rwa-dd/2.1 fixture (same ledger), with v0.6.0 outputs in place."""
    project = _final(tmp_path)
    state = runstate.load_state(project)
    work = runstate.load_work(project)
    old = load_v21()
    old["run"] = dict(work["run"], skill_version="0.6.0")
    old["sources"] = work["sources"]
    project.work_file.write_bytes(dump_json(old).encode("utf-8"))
    project.output("dd.json").write_bytes(dump_json(old).encode("utf-8"))
    return project, state["run_id"], old


@pytest.mark.d2
@NEEDS_D2
def test_seed_from_final_v21_run(tmp_path):
    project, old_id, old = _final_v21(tmp_path)
    runstate.seed(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at(LATER))
    doc = runstate.load_work(project)
    assert doc == migrate.convert_21(old, doc["run"])
    assert runstate.check(tmp_path, "acme") == []
    assert (project.archive / old_id / "acme.derived.json").is_file()
    assert [f["scope_note"] for f in doc["findings"] if f["type"] in ("discrepancy", "scope_unresolved")][2] == \
        schema.MIGRATED_NOTE_21
    runstate.make_review(tmp_path, "acme")
    review = (project.round_dir(1) / "review.md").read_bytes().decode("utf-8")
    assert "| QA9 | placeholder | fail | -- | -- | D1, D2, U1, X2.amounts\\[0\\], X4.amounts\\[0\\]," in review
    _directives(tmp_path, project, "finalize\n", name="seeded.txt")
    with pytest.raises(runstate.ContractError) as exc:
        runstate.finalize(tmp_path, "acme", clock=clock_at(LATER))
    assert str(exc.value) == "D1: scope not checked (scope_note is a migration placeholder)"
    # The change log of the seeded run compares with the migrated earlier record: nothing changed yet.
    assert runstate.change_rows(tmp_path, "acme") == []


def _ready_fixture(tmp_path, mutate):
    project = _to_awaiting(tmp_path)
    doc = runstate.load_work(project)
    mutate(doc)
    runstate.save_work(project, doc)
    _directives(tmp_path, project, "finalize\n")
    return project


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["findings"][4].update({"scope_note": schema.MIGRATED_NOTE_21 + " -- old"}),
     "D2: scope not checked (scope_note is a migration placeholder)"),
    (lambda d: d["findings"][6].update({"scope_note": schema.MIGRATED_SCOPE_NOTE}),
     "U1: scope not checked (scope_note is a migration placeholder)"),
    (lambda d: d["interfaces"][8]["amounts"][0].update({"scope": schema.MIGRATED_AMOUNT_SCOPE}),
     "X9.amounts[0]: amount scope not checked (migration placeholder)"),
    (lambda d: d["interfaces"][1]["amounts"][1]["value"].update({"evidence": ["S8", "S9"]}),
     "QA failed: QA7"),
])
def test_finalize_refusals(tmp_path, monkeypatch, mutate, message):
    project = _ready_fixture(tmp_path, mutate)
    assert runstate.check(tmp_path, "acme") == []
    before = _snapshot(project)
    monkeypatch.setattr(flow, "find_d2", lambda: None)  # refusals come before the d2 check
    with pytest.raises(runstate.ContractError) as exc:
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert str(exc.value) == message
    assert _snapshot(project) == before


def test_finalize_refuses_failing_expectation(tmp_path, monkeypatch):
    project = _ready_fixture(tmp_path, lambda d: None)
    expect = [{"id": "x2-basis", "case": "X2 entry 0 is a balance", "path": "X2.amounts[0].basis", "op": "equals",
               "value": "POSITION_VALUE"}]
    (project.audit / "qa-expect.json").write_bytes(json.dumps(expect).encode("utf-8"))
    monkeypatch.setattr(flow, "find_d2", lambda: None)
    with pytest.raises(runstate.ContractError) as exc:
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert str(exc.value) == "QA failed: E:x2-basis"
    (project.audit / "qa-expect.json").write_bytes(b"[{}]")
    with pytest.raises(runstate.ContractError) as exc:
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert str(exc.value) == "expectations[0]: keys must be id, case, path, op, value, optionally target"
    (project.audit / "qa-expect.json").write_bytes(
        b'[{"id": "a", "case": "c", "path": "@G3.type", "op": "exists", "value": true}]')
    with pytest.raises(runstate.ContractError) as exc:
        runstate.finalize(tmp_path, "acme", clock=clock_at())
    assert str(exc.value) == "expectations[0].target: required for a legacy (@) path"


@pytest.mark.d2
@NEEDS_D2
def test_finalize_writes_derived_json(tmp_path):
    project = _final(tmp_path)
    record = project.output("dd.json").read_bytes()
    derived = json.loads(project.output("derived.json").read_bytes().decode("utf-8"))
    assert derived["record_sha256"] == hashlib.sha256(record).hexdigest()
    assert list(derived) == sorted(derived)
    assert (derived["derived_version"], derived["slug"], derived["schema_version"], derived["skill_version"]) == \
        ("rwa-dd-derived/1", "acme", "rwa-dd/2.2", schema.SKILL_VERSION)
    assert derived["flags"]["X6.terms"] == "CONFLICTING" and derived["critical"] == ["R1", "G1", "G3", "U1"]
    assert derived["critical_counts"] == {"open_not_selected": 2, "selected": 4, "total": 8}
    assert derived["conflicts"][0] == {"assertion_sources": ["S7", "S1"], "conflict_status": "CONFLICTING",
                                       "finding": "D1", "resolution": "open", "scope_match": "matched",
                                       "subjects": ["X6.terms"]}
    assert [q for q, _ in derived["five_questions"]["T1"]][-1] == "Is deployment verified?"
    assert sorted(derived["five_questions"]) == ["T1", "T2"]
    assert [r["id"] for r in derived["qa"]] == ["QA%d" % i for i in range(1, 14)] and derived["changes"] == []
    assert derived["allocation"][0]["valuation_basis"] is None and derived["allocation"][1]["reason"] == "other measure of X2[0]"
    assert (derived["allocation"][0]["time_basis"], derived["allocation"][0]["observed_at"]) == (
        "block", "2026-10-01T08:15:00Z")
    assert {(r["target"], r["legacy"], r["mapping"]) for r in derived["qa"]} == {(None, None, "")}
    text = project.output("derived.json").read_bytes()
    assert text.endswith(b"}\n") and b"\r" not in text


def test_render_draft_writes_derived_copy(tmp_path, monkeypatch):
    project = build_run(tmp_path)
    monkeypatch.setattr(flow, "find_d2", lambda: None)
    runstate.render_draft(tmp_path, "acme", clock=clock_at())
    derived = json.loads((project.scratch / "draft" / "acme.derived.json").read_bytes().decode("utf-8"))
    assert derived["run_id"] == "acme-20261001T080000Z" and derived["qa"][8]["id"] == "QA9"
    report = (project.scratch / "draft" / "acme.report.md").read_bytes().decode("utf-8")
    assert "| Report generated | draft 2026-10-01 |" in report
    assert not any(p.exists() for p in project.outputs())


def test_status_prints_run_scoped_log_names(tmp_path):
    project = _to_awaiting(tmp_path)
    run_id = runstate.load_state(project)["run_id"]
    out = runstate.status(tmp_path, "acme")
    assert out["next_directives_log"] == ".scratch/logs/%s-directives-r1.txt" % run_id
    assert out["next_amend_log"] == ".scratch/logs/%s-amend-1.txt" % run_id
    _directives(tmp_path, project, "accept N1\n")
    assert runstate.status(tmp_path, "acme")["next_directives_log"] == \
        ".scratch/logs/%s-directives-r2.txt" % run_id
    state = dict(runstate.load_state(project), amendment=2)
    assert runstate.log_name(state, "amend", state["amendment"] + 1) == ".scratch/logs/%s-amend-3.txt" % run_id


def test_change_log_of_seeded_run(tmp_path):
    project = build_run(tmp_path)
    old_id = runstate.load_state(project)["run_id"]
    old = load_v21()
    old["run"] = runstate.load_work(project)["run"]
    old["sources"] = runstate.load_work(project)["sources"][:8]
    fixture_findings = runstate.load_work(project)["findings"]
    runstate.seed(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at(LATER))
    assert runstate.change_rows(tmp_path, "acme") == []  # no earlier final record in the archive
    doc = runstate.load_work(project)
    doc["findings"] = fixture_findings  # re-typed in this run: R1 carried from G3
    runstate.save_work(project, doc)
    archive = project.archive / old_id
    (archive / "acme.dd.json").write_bytes(dump_json(old).encode("utf-8"))
    rows = runstate.change_rows(tmp_path, "acme")
    assert {"ref": "G3 -> R1", "path": "type", "change": "changed", "before": "gap",
            "after": "unreconciled_transaction", "evidence_added": []} in rows
    assert any(r["ref"] == "S9" and r["change"] == "added" for r in rows)
