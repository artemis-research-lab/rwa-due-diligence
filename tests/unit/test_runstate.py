"""Test groups 5 (path safety) and 6 (state machine)."""

import os

import pytest

from test_support import GOLDEN, build_run, clock_at, walk
from lib import flow, runstate

# finalize requires d2 v0.9.0 since P3; these tests run only where it is on PATH (see test_flow.py).
NEEDS_D2 = pytest.mark.skipif(flow.find_d2() is None, reason="d2 %s not on PATH" % flow.D2_VERSION)


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
    assert runstate.check(tmp_path, "acme") == ["project.products[0]: P1 has no flow edge",
                                                "project.products[0]: P1 has no yield entry"]


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
    assert (archive / "acme.flow-P1.svg").is_file() and (archive / "acme.flow-P2.svg").is_file()
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
    assert text.startswith('{\n  "schema_version": "rwa-dd/1.0",\n  "run": {\n    "run_id"')
    assert '"finalized_at": "2026-10-01T08:00:00Z"' in text


def test_render_draft_any_phase(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    out = runstate.render_draft(tmp_path, "acme")
    assert out["outputs"][0].endswith(os.path.join(".scratch", "draft", "acme.report.md"))
    assert open(out["outputs"][0], encoding="utf-8").read().startswith("# RWA Due Diligence: acme\n")
    assert out["outputs"][1].endswith(os.path.join(".scratch", "draft", "acme.report.html"))
    assert "<h1>RWA Due Diligence: acme</h1>" in open(out["outputs"][1], encoding="utf-8").read()


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
    assert [os.path.basename(p) for p in out["outputs"]] == ["acme.report.md", "acme.report.html"]
    page = open(out["outputs"][1], encoding="utf-8").read()
    assert '<figure class="dd-flow" id="flow-P1"></figure>' in page and "<svg" not in page
    assert "![Fund flow" not in open(out["outputs"][0], encoding="utf-8").read()


@pytest.mark.d2
@NEEDS_D2
def test_render_draft_with_d2_writes_svgs(tmp_path):
    project = build_run(tmp_path)
    out = runstate.render_draft(tmp_path, "acme")
    assert "warnings" not in out
    names = [os.path.basename(p) for p in out["outputs"]]
    assert names == ["acme.report.md", "acme.report.html", "acme.flow-P1.svg", "acme.flow-P2.svg"]
    assert all(os.path.dirname(p) == str(project.scratch / "draft") for p in out["outputs"])
    assert '<figure class="dd-flow" id="flow-P1">\n<svg ' in open(out["outputs"][1], encoding="utf-8").read()


@pytest.mark.d2
@NEEDS_D2
def test_finalize_with_d2_writes_svgs_in_outputs(tmp_path):
    project = _ready(tmp_path)
    result = runstate.finalize(tmp_path, "acme", clock=clock_at())
    names = [os.path.basename(p) for p in result["outputs"]]
    assert names == ["acme.dd.json", "acme.report.md", "acme.report.html", "acme.flow-P1.svg", "acme.flow-P2.svg"]
    for pid in ("P1", "P2"):
        assert project.flow_output(pid).read_bytes() == (GOLDEN / ("acme.flow-%s.svg" % pid)).read_bytes()
    md = project.output("report.md").read_bytes().decode("utf-8")
    assert "![Fund flow P1](acme.flow-P1.svg)" in md and "![Fund flow P2](acme.flow-P2.svg)" in md
    assert [p.name for p in project.outputs()] == names

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
    s2 = md[md.index("## 2. Blocking gaps"):md.index("## 3. Products")]
    assert "**G1**" in s2 and "**N" not in s2
    d = md[md.index("## Appendix D. Searches not run"):]
    assert "- **N1** Custody agreement and issuer accounts" in d
    assert "(resolves G1; est 6 calls) -- rejected by the analyst\n" in d
    assert "(resolves G2, D1; est 4 calls) -- not run\n" in d
    page = project.output("report.html").read_bytes().decode("utf-8")
    assert "est 6 calls) -- rejected by the analyst</li>" in page


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
    assert runstate.load_work(project)["run"]["skill_version"] == "0.4.2"

    later = clock_at(__import__("datetime").datetime(2026, 11, 1, tzinfo=__import__("datetime").timezone.utc))
    runstate.init(tmp_path, "acme", "https://acme-yield.example/", clock=later, new_run=True)
    assert (project.archive / run_id / "audit" / "state.json").is_file()
    assert (project.archive / ("%s.v0" % run_id) / "acme.dd.json").is_file()
    assert (project.archive / ("%s.v0" % run_id) / "acme.report.md").is_file()


def test_runstate_ends_with_single_newline():
    data = (GOLDEN.parents[1] / "lib" / "runstate.py").read_bytes()
    assert data.endswith(b"\n") and not data.endswith(b"\n\n")