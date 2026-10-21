"""Package manifest and verification (v0.7.2 section 3, curator AC-04).

manifest() describes a finalized run: every output, the ledger, the expectations, the run state, the round records
and the analyst inputs of the run with byte counts and SHA-256, plus execution metadata and the check results.
verify() recomputes all of it read-only. Neither writes anything; lib/runstate.py writes the manifest.
"""

import hashlib
import platform

from lib import flow, ledger, lint, qa, validate
from lib.textutil import load_json_text

MANIFEST_VERSION = "rwa-dd-manifest/1"
EXPECT_FILE = "qa-expect.json"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _relative(project, path):
    return path.relative_to(project.dir).as_posix()


def _listed(project, state):
    """[(path, role), ...] of the package files that exist, sorted by relative path; never the manifest."""
    found = [(project.output("dd.json"), "record"), (project.output("derived.json"), "derived"),
             (project.output("report.md"), "report"), (project.ledger_file, "ledger"),
             (project.audit / EXPECT_FILE, "expectations"), (project.state_file, "run_state")]
    found += [(path, "diagram") for path in project.flow_outputs()]
    if project.rounds.is_dir():
        found += [(path, "round_record") for path in project.rounds.glob("r*/**/*") if path.is_file()]
    logs = project.scratch / "logs"
    if logs.is_dir():
        found += [(path, "analyst_input") for path in logs.glob("%s-*" % state["run_id"]) if path.is_file()]
    found = [(path, role) for path, role in found if path.is_file()]
    return sorted(found, key=lambda item: _relative(project, item[0]))


def _expectations(project, files):
    """Expectation entries of the listed expectation file; [] when none is listed."""
    for entry in files:
        if entry["role"] == "expectations":
            path = project.dir / entry["path"]
            return qa.parse_expectations(path.read_bytes().decode("utf-8"), path.name)
    return []


def _checks(project, record_bytes, derived, expectations):
    doc = load_json_text(record_bytes.decode("utf-8"))
    errors = validate.validate_document(doc, ledger.read_ledger(project.ledger_file))
    results = qa.run(doc, expectations) if not errors else []
    return doc, errors, results, {
        "validate_errors": len(errors),
        "lint_warnings": len(lint.lint(doc)) if not errors else 0,
        "qa_failed": qa.failed(results),
        "record_sha256_match": derived.get("record_sha256") == _sha256(record_bytes),
    }


def manifest(project, state, doc):
    """The <slug>.manifest.json object of a finalized run (written by finalize after every other file)."""
    files = []
    for path, role in _listed(project, state):
        data = path.read_bytes()
        files.append({"path": _relative(project, path), "role": role, "bytes": len(data), "sha256": _sha256(data)})
    record = project.output("dd.json").read_bytes()
    derived = load_json_text(project.output("derived.json").read_bytes().decode("utf-8"))
    _, _, _, checks = _checks(project, record, derived, _expectations(project, files))
    run = doc["run"]
    return {
        "manifest_version": MANIFEST_VERSION, "slug": project.slug, "run_id": state["run_id"],
        "seeded_from": run["seeded_from"], "schema_version": doc["schema_version"],
        "skill_version": run["skill_version"], "finalized_at": run["finalized_at"], "rounds": state["round"],
        "execution": {"python": platform.python_version(), "platform": platform.system(),
                      "d2": flow.d2_version()},
        "files": files,
        "checks": checks,
    }


def _qa_key(results):
    return [(r.get("id"), r.get("result"), r.get("target")) for r in results]


def verify(project):
    """{"result": "PASS"|"FAIL", "failures": [...]} for the package of a finalized run; reads only."""
    path = project.output("manifest.json")
    if not path.is_file():
        return {"result": "FAIL", "failures": ["%s: missing" % path.name]}
    try:
        man = load_json_text(path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return {"result": "FAIL", "failures": ["%s: not valid JSON: %s" % (path.name, exc)]}
    failures = []
    if man.get("manifest_version") != MANIFEST_VERSION or man.get("slug") != project.slug:
        failures.append("%s: not a %s manifest of %s" % (path.name, MANIFEST_VERSION, project.slug))
        return {"result": "FAIL", "failures": failures}
    files = man.get("files") or []
    for entry in files:
        target = project.dir / entry["path"]
        try:
            project.safe(target)
        except Exception:
            failures.append("%s: outside the project directory" % entry["path"])
            continue
        if not target.is_file():
            failures.append("%s: missing" % entry["path"])
            continue
        data = target.read_bytes()
        if len(data) != entry["bytes"]:
            failures.append("%s: bytes %d, manifest %d" % (entry["path"], len(data), entry["bytes"]))
        if _sha256(data) != entry["sha256"]:
            failures.append("%s: sha256 differs from the manifest" % entry["path"])
    roles = {entry["role"] for entry in files}
    for role in ("record", "derived", "report", "ledger", "run_state"):
        if role not in roles:
            failures.append("files: no %s listed" % role)
    if failures:
        return {"result": "FAIL", "failures": failures}

    record = project.output("dd.json").read_bytes()
    derived = load_json_text(project.output("derived.json").read_bytes().decode("utf-8"))
    try:
        expectations = _expectations(project, files)
    except qa.ExpectationError as exc:
        return {"result": "FAIL", "failures": ["expectations: %s" % exc]}
    doc, errors, results, checks = _checks(project, record, derived, expectations)
    stated = man.get("checks") or {}
    if errors:
        failures.append("validate: %d errors (first: %s)" % (len(errors), sorted(errors)[0]))
    for key in ("validate_errors", "lint_warnings", "qa_failed", "record_sha256_match"):
        if checks[key] != stated.get(key):
            failures.append("checks.%s: recomputed %s, manifest %s" % (key, checks[key], stated.get(key)))
    if not checks["record_sha256_match"]:
        failures.append("derived.json: record_sha256 does not match %s" % project.output("dd.json").name)
    if not errors and _qa_key(results) != _qa_key(derived.get("qa") or []):
        failures.append("derived.json: QA results (id, result, target) differ from the recomputed ones")
    for key in ("run_id", "schema_version", "skill_version", "finalized_at", "seeded_from"):
        expected = doc["run"].get(key) if key != "schema_version" else doc.get(key)
        if man.get(key) != expected:
            failures.append("%s: manifest %s, record %s" % (key, man.get(key), expected))
    return {"result": "PASS" if not failures else "FAIL", "failures": failures}
