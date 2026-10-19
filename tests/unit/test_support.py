"""Shared helpers for the unit tests (no tests here)."""

import contextlib
import copy
import datetime
import importlib.util
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import runstate  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"
FIXED = datetime.datetime(2026, 10, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)


def load_fixture():
    return json.loads((FIXTURES / "acme.dd.json").read_bytes().decode("utf-8"))


def load_v1():
    """The rwa-dd/1.0 fixture (same ledger as acme.dd.json), used by the migration tests."""
    return json.loads((FIXTURES / "acme_v1.dd.json").read_bytes().decode("utf-8"))


def fixture_sources():
    lines = (FIXTURES / "acme.sources.jsonl").read_bytes().decode("utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def clock_at(moment=FIXED):
    return lambda: moment


def clock_from_ts(ts):
    if ts is None:
        return clock_at()
    return clock_at(datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc))


def source_fields(source):
    """add-source keyword arguments that recreate a fixture source."""
    return {"url": source["url"], "title": source["title"], "source_type": source["source_type"],
            "origin": source["origin"], "fetch": source["fetch"], "excerpt": source["excerpt"],
            "publisher": source["publisher"], "archived": source["archived"],
            "version_date": source["version_date"], "note": source["note"],
            "offline": source["retrieved_at"] is None}


def source_argv(source):
    argv = ["--url", source["url"], "--title", source["title"], "--source-type", source["source_type"],
            "--origin", source["origin"], "--fetch", source["fetch"], "--excerpt", source["excerpt"]]
    if source["publisher"]:
        argv += ["--publisher", source["publisher"]]
    if source["archived"]:
        argv.append("--archived")
    if source["version_date"]:
        argv += ["--version-date", source["version_date"]]
    if source["note"]:
        argv += ["--note", source["note"]]
    if source["retrieved_at"] is None:
        argv.append("--offline")
    return argv


def merge_fixture_body(project, fixture):
    """Write every fixture section except schema_version/run/sources into dd.work.json."""
    doc = runstate.load_work(project)
    for key, value in fixture.items():
        if key not in ("schema_version", "run", "sources"):
            doc[key] = copy.deepcopy(value)
    runstate.save_work(project, doc)
    return doc


def build_run(root, fixture=None):
    """A run directory whose ledger and working document equal the fixture (except the run block)."""
    fixture = load_fixture() if fixture is None else fixture
    runstate.init(root, "acme", fixture["run"]["root_url"], clock=clock_at())
    for source in fixture["sources"]:
        runstate.add_source(root, "acme", clock=clock_from_ts(source["retrieved_at"]), **source_fields(source))
    project = runstate.open_project(root, "acme")
    merge_fixture_body(project, fixture)
    return project


def load_cli():
    spec = importlib.util.spec_from_file_location("dd_cli", ROOT / "scripts" / "dd.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = load_cli().main(argv)
    return code, out.getvalue(), err.getvalue()


def walk(path):
    return sorted(str(p.relative_to(path)) for p in Path(path).rglob("*"))
