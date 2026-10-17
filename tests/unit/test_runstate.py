"""Test groups 5 (path safety) and 6 (state machine)."""

import os

import pytest

from test_support import build_run, clock_at, walk
from lib import runstate


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
    assert (archive / "audit" / "state.json").is_file()
    assert not any(p.exists() for p in project.outputs())
    assert runstate.load_state(project)["run_id"] == out["run_id"] == "acme-20261101T000000Z"


def test_init_on_draft_refused_without_new_run(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    with pytest.raises(runstate.ContractError):
        runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())


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
