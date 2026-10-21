"""v0.7.2 section 3 (curator AC-04): package manifest and dd.py verify (lib/package.py)."""

import hashlib
import json
import platform

import pytest

from test_support import FIXTURES, build_run, clock_at, load_cli, load_fixture, run_cli, walk
from lib import flow, lint, package, runstate, schema

NEEDS_D2 = pytest.mark.skipif(flow.find_d2() is None, reason="d2 %s not on PATH" % flow.D2_VERSION)
pytestmark = [pytest.mark.d2, NEEDS_D2]
LATER = __import__("datetime").datetime(2026, 11, 1, tzinfo=__import__("datetime").timezone.utc)
DIAGRAMS = ["acme.flow-T1-claim.svg", "acme.flow-T1-repayment.svg", "acme.flow-T1-settlement.svg",
            "acme.flow-T2-settlement.svg"]


def _log(project, name, text):
    path = project.dir / name
    path.write_bytes(text.encode("utf-8"))
    return path


def _finalize(tmp_path, project, clock=clock_at()):
    """Review, a run-scoped finalize directives log, finalize."""
    runstate.make_review(tmp_path, "acme")
    state = runstate.load_state(project)
    log = _log(project, runstate.log_name(state, "directives", state["round"]), "finalize\n")
    runstate.apply_directives(tmp_path, "acme", log)
    runstate.finalize(tmp_path, "acme", clock=clock)
    return json.loads(project.output("manifest.json").read_bytes().decode("utf-8"))


def _final(tmp_path):
    project = build_run(tmp_path)
    (project.audit / "qa-expect.json").write_bytes((FIXTURES / "acme.qa-expect.json").read_bytes())
    return project, _finalize(tmp_path, project)


def test_manifest_files_roles_and_metadata(tmp_path):
    project, manifest = _final(tmp_path)
    run_id = runstate.load_state(project)["run_id"]
    assert list(manifest) == ["manifest_version", "slug", "run_id", "seeded_from", "schema_version", "skill_version",
                              "finalized_at", "rounds", "execution", "files", "checks"]
    assert (manifest["manifest_version"], manifest["slug"], manifest["run_id"], manifest["seeded_from"],
            manifest["schema_version"], manifest["skill_version"], manifest["finalized_at"], manifest["rounds"]) == (
        "rwa-dd-manifest/1", "acme", run_id, None, "rwa-dd/2.2", schema.SKILL_VERSION, "2026-10-01T08:00:00Z", 1)
    assert manifest["execution"] == {"python": platform.python_version(), "platform": platform.system(),
                                     "d2": flow.D2_VERSION}
    assert [(f["path"], f["role"]) for f in manifest["files"]] == [
        (".scratch/logs/%s-directives-r1.txt" % run_id, "analyst_input"),
        ("acme.dd.json", "record"), ("acme.derived.json", "derived")] + [
        (name, "diagram") for name in DIAGRAMS] + [
        ("acme.report.md", "report"), ("audit/qa-expect.json", "expectations"),
        ("audit/rounds/r1/directives.json", "round_record"), ("audit/rounds/r1/directives.txt", "round_record"),
        ("audit/rounds/r1/review.md", "round_record"), ("audit/sources.jsonl", "ledger"),
        ("audit/state.json", "run_state")]
    for entry in manifest["files"]:
        data = (project.dir / entry["path"]).read_bytes()
        assert (entry["bytes"], entry["sha256"]) == (len(data), hashlib.sha256(data).hexdigest())
    record = json.loads(project.output("dd.json").read_bytes().decode("utf-8"))
    assert manifest["checks"] == {"validate_errors": 0, "lint_warnings": 0,
                                  "lint_by_key": {key: 0 for key in sorted(lint.lint(record))}, "qa_failed": [],
                                  "record_sha256_match": True}
    assert len(manifest["checks"]["lint_by_key"]) == 6
    text = project.output("manifest.json").read_bytes()
    assert text.endswith(b"}\n") and b"\r" not in text


def test_manifest_counts_lint_warnings_not_keys(tmp_path):
    fixture = load_fixture()
    x2 = next(x for x in fixture["interfaces"] if x["id"] == "X2")
    assert x2["kind"] == "L1_L2" and x2["amounts"][2]["basis"] == "CUMULATIVE_FUNDED"
    x2["amounts"][2]["as_of"] = None  # one amount warning: data time not established
    project = build_run(tmp_path, fixture)
    manifest = _finalize(tmp_path, project)
    by_key = manifest["checks"]["lint_by_key"]
    assert manifest["checks"]["lint_warnings"] == 1 and list(by_key) == sorted(by_key) and len(by_key) == 6
    assert by_key == dict({key: 0 for key in by_key}, amount_warnings=1)
    assert package.verify(project) == {"result": "PASS", "failures": []}


def test_verify_fails_when_manifest_lint_count_is_edited(tmp_path):
    project, manifest = _final(tmp_path)
    manifest["checks"]["lint_warnings"] = 6
    project.output("manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    assert package.verify(project) == {"result": "FAIL", "failures": ["checks.lint_warnings: recomputed 0, manifest 6"]}


def test_seeded_run_lists_its_logs_only(tmp_path):
    project, first = _final(tmp_path)
    old_id = first["run_id"]
    _log(project, runstate.log_name(runstate.load_state(project), "amend", 1), "note kept for the old run\n")
    runstate.seed(tmp_path, "acme", "https://acme-yield.example/", clock=clock_at(LATER))
    state = runstate.load_state(project)
    _log(project, ".scratch/logs/%s-notes.txt" % state["run_id"], "analyst notes\n")
    manifest = _finalize(tmp_path, project, clock=clock_at(LATER))
    assert (manifest["seeded_from"], manifest["run_id"]) == (old_id, state["run_id"])
    inputs = [f["path"] for f in manifest["files"] if f["role"] == "analyst_input"]
    assert inputs == [".scratch/logs/%s-directives-r1.txt" % state["run_id"],
                      ".scratch/logs/%s-notes.txt" % state["run_id"]]
    assert "audit/qa-expect.json" not in [f["path"] for f in manifest["files"]]
    assert (project.archive / old_id / "acme.manifest.json").is_file()
    assert package.verify(project) == {"result": "PASS", "failures": []}


def test_verify_passes_and_writes_nothing(tmp_path):
    project, _ = _final(tmp_path)
    before = [(p, (project.dir / p).read_bytes()) for p in walk(project.dir) if (project.dir / p).is_file()]
    assert package.verify(project) == {"result": "PASS", "failures": []}
    after = [(p, (project.dir / p).read_bytes()) for p in walk(project.dir) if (project.dir / p).is_file()]
    assert after == before


def _flip(path, offset=10):
    data = bytearray(path.read_bytes())
    data[offset] = ord("#") if data[offset] != ord("#") else ord("%")
    path.write_bytes(bytes(data))


@pytest.mark.parametrize("name", ["acme.report.md", "audit/sources.jsonl", "acme.derived.json"])
def test_verify_fails_after_one_byte_changes(tmp_path, name):
    project, _ = _final(tmp_path)
    _flip(project.dir / name)
    result = package.verify(project)
    assert result["result"] == "FAIL"
    assert result["failures"] == ["%s: sha256 differs from the manifest" % name]


def test_verify_recomputes_checks_not_only_hashes(tmp_path):
    project, manifest = _final(tmp_path)
    derived_path = project.output("derived.json")
    derived = json.loads(derived_path.read_bytes().decode("utf-8"))
    derived["qa"][-1]["target"] = "X2"  # the regression result now names a different target
    data = (json.dumps(derived, indent=2, sort_keys=True) + "\n").encode("utf-8")
    derived_path.write_bytes(data)
    for entry in manifest["files"]:
        if entry["path"] == "acme.derived.json":
            entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    project.output("manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    assert package.verify(project) == {"result": "FAIL", "failures": [
        "derived.json: QA results (id, result, target) differ from the recomputed ones"]}


def test_verify_missing_manifest_and_missing_file(tmp_path):
    project, _ = _final(tmp_path)
    (project.dir / "audit" / "rounds" / "r1" / "review.md").unlink()
    assert package.verify(project) == {"result": "FAIL", "failures": ["audit/rounds/r1/review.md: missing"]}
    project.output("manifest.json").unlink()
    assert package.verify(project) == {"result": "FAIL", "failures": ["acme.manifest.json: missing"]}


def test_verify_cli_exit_codes(tmp_path):
    project, _ = _final(tmp_path)
    code, out, err = run_cli(["verify", "--slug", "acme", "--root", str(tmp_path)])
    assert (code, err) == (0, "") and json.loads(out) == {"result": "PASS", "failures": []}
    _flip(project.output("report.md"))
    code, out, _ = run_cli(["verify", "--slug", "acme", "--root", str(tmp_path)])
    assert code == 6 and json.loads(out) == {"result": "FAIL", "failures": [
        "acme.report.md: sha256 differs from the manifest"]}
    help_text = load_cli().build_parser().format_help()
    assert "6 package does not reproduce (verify only)" in " ".join(help_text.split())
