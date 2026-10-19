"""Test group 10: end-to-end through the CLI in a temporary reports root."""

import json
import os
from pathlib import Path

import pytest

from test_support import build_run, load_fixture, merge_fixture_body, run_cli, source_argv, walk
from lib import flow, runstate

NEEDS_D2 = pytest.mark.skipif(flow.find_d2() is None, reason="d2 %s not on PATH" % flow.D2_VERSION)


def cli(root, *argv):
    return run_cli(list(argv[:1]) + ["--slug", "acme", "--root", str(root)] + list(argv[1:]))


@pytest.mark.d2
@NEEDS_D2
def test_e2e_two_rounds_to_finalize(tmp_path, capsys):
    fixture = load_fixture()
    before = walk(tmp_path)
    assert cli(tmp_path, "init", "--url", fixture["run"]["root_url"])[0] == 0

    for source in fixture["sources"]:
        code, out, err = cli(tmp_path, "add-source", *source_argv(source))
        assert (code, err) == (0, "")
        got = json.loads(out)
        assert {k: v for k, v in got.items() if k != "retrieved_at"} == \
            {k: v for k, v in source.items() if k != "retrieved_at"}
        assert (got["retrieved_at"] is None) == (source["retrieved_at"] is None)

    project = runstate.open_project(tmp_path, "acme")
    merge_fixture_body(project, fixture)
    assert cli(tmp_path, "validate")[:2] == (0, "valid\n")

    code, out, _ = cli(tmp_path, "review")
    assert code == 0 and json.loads(out)["round"] == 1
    reply = project.scratch / "logs" / "r1.txt"
    reply.write_bytes(b"accept N1\n")
    assert cli(tmp_path, "directives", "--file", str(reply))[0] == 0

    code, out, _ = cli(tmp_path, "status")
    status = json.loads(out)
    assert status["state"]["round"] == 2 and status["state"]["phase"] == "research" and status["valid"]

    assert cli(tmp_path, "review")[0] == 0
    reply2 = project.scratch / "logs" / "r2.txt"
    reply2.write_bytes(b"note good enough\nfinalize\n")
    assert cli(tmp_path, "directives", "--file", str(reply2))[0] == 0

    code, out, err = cli(tmp_path, "finalize")
    assert (code, err) == (0, "")
    result = json.loads(out)
    with capsys.disabled():
        print("\nFINALIZE_JSON " + json.dumps(result))
    assert list(result) == ["project_dir", "outputs", "audit_dir", "scratch_dir", "rounds"]
    assert result["rounds"] == 2
    base = (tmp_path / "acme").resolve()
    assert Path(result["project_dir"]) == base
    assert [Path(p).name for p in result["outputs"]] == ["acme.dd.json", "acme.report.md",
                                                         "acme.flow-T1-settlement.svg", "acme.flow-T1-claim.svg",
                                                         "acme.flow-T1-repayment.svg", "acme.flow-T2-settlement.svg"]
    for p in result["outputs"] + [result["audit_dir"], result["scratch_dir"]]:
        assert os.path.exists(p) and base in Path(p).resolve().parents

    final = json.loads(Path(result["outputs"][0]).read_bytes().decode("utf-8"))
    assert final["run"]["status"] == "final" and final["run"]["round"] == 2
    report = Path(result["outputs"][1]).read_bytes().decode("utf-8")
    assert "### Round 1\n\n```text\naccept N1\n```" in report
    assert "### Round 2\n\n```text\nnote good enough\nfinalize\n```" in report
    assert "DRAFT" not in report

    # Nothing was created outside <tmp>/acme.
    assert before == []
    assert all(p == "acme" or p.startswith("acme" + os.sep) for p in walk(tmp_path))


def test_exit_codes(tmp_path):
    assert cli(tmp_path, "validate")[0] == 3            # no run yet
    assert run_cli(["init", "--slug", "../x", "--url", "u", "--root", str(tmp_path)])[0] == 3
    assert cli(tmp_path, "init", "--url", "https://a.example/")[0] == 0
    code, out, _ = cli(tmp_path, "validate")
    assert code == 2 and out == ("project.products[0]: P1 has no yield entry\n"
                                 "strategies[0]: T1 has no flow edge with view settlement\n")
    assert cli(tmp_path, "review")[0] == 2
    assert cli(tmp_path, "finalize")[0] == 3
    code, _, err = cli(tmp_path, "init", "--url", "https://a.example/")
    assert code == 3 and 'run exists (phase research); use "dd.py status" to inspect or --new-run' in err


def test_render_writes_draft_markdown_only(tmp_path):
    assert cli(tmp_path, "init", "--url", "https://a.example/")[0] == 0
    code, out, _ = cli(tmp_path, "render")
    assert code == 0
    draft = tmp_path / "acme" / ".scratch" / "draft"
    assert (draft / "acme.report.md").is_file() and not (draft / "acme.report.html").exists()
    assert "> DRAFT -- not finalized\n" in (draft / "acme.report.md").read_bytes().decode("utf-8")


def test_init_seed_from_cli(tmp_path):
    build_run(tmp_path)
    old_id = runstate.load_state(runstate.open_project(tmp_path, "acme"))["run_id"]
    code, out, err = cli(tmp_path, "init", "--url", "https://acme-yield.example/", "--seed-from")
    assert (code, err) == (0, "")
    result = json.loads(out)
    assert list(result) == ["project_dir", "run_id", "work_file", "seeded_from", "sources"]
    assert result["seeded_from"] == old_id and result["sources"] == 8 and result["run_id"] != old_id
    assert cli(tmp_path, "validate")[:2] == (0, "valid\n")


def test_init_seed_from_errors(tmp_path):
    code, _, err = cli(tmp_path, "init", "--url", "https://a.example/", "--seed-from")
    assert code == 3 and "to seed from" in err
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf), pytest.raises(SystemExit) as exc:
        from test_support import load_cli
        load_cli().main(["init", "--slug", "acme", "--root", str(tmp_path), "--url", "u", "--seed-from",
                         "--new-run"])
    assert exc.value.code == 2 and "not allowed with argument" in buf.getvalue()


def test_help_lists_all_commands():
    code, out, _ = run_cli(["schema-doc"])
    assert code == 0
    import contextlib
    import io
    import pytest
    from test_support import load_cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit):
        load_cli().main(["--help"])
    for name in ("init", "add-source", "validate", "lint", "review", "directives", "render", "status", "finalize",
                 "schema-doc"):
        assert name in buf.getvalue()


def _ready(tmp_path):
    project = build_run(tmp_path)
    runstate.make_review(tmp_path, "acme")
    reply = project.scratch / "logs" / "r1.txt"
    reply.write_bytes(b"finalize\n")
    runstate.apply_directives(tmp_path, "acme", reply)
    return project


def test_finalize_without_d2_exit_4(tmp_path, monkeypatch):
    project = _ready(tmp_path)
    before = walk(tmp_path)
    monkeypatch.setattr(flow, "find_d2", lambda: None)
    code, out, err = cli(tmp_path, "finalize")
    assert (code, out) == (4, "")
    assert err == "dependency error: d2 v0.9.0 required, found none on PATH\n"
    assert walk(tmp_path) == before
    assert runstate.load_state(project)["phase"] == "ready_to_finalize"


def test_render_without_d2_warns(tmp_path, monkeypatch):
    build_run(tmp_path)
    monkeypatch.setattr(flow, "find_d2", lambda: None)
    code, out, _ = cli(tmp_path, "render")
    assert code == 0 and json.loads(out)["warnings"] == ["d2 v0.9.0 not found: diagrams omitted"]


def test_help_mentions_exit_4():
    import contextlib
    import io
    from test_support import load_cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit):
        load_cli().main(["--help"])
    assert "4 diagram renderer d2 missing" in " ".join(buf.getvalue().split())


# P4 helpers ----------------------------------------------------------------------------------------------

def test_help_lists_research_helpers():
    import contextlib
    import io
    from test_support import load_cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit):
        load_cli().main(["--help"])
    assert "fetch-file" in buf.getvalue() and "pdf-text" in buf.getvalue()


def test_fetch_file_and_pdf_text_cli(tmp_path, monkeypatch):
    from test_fetch import FakeResponse, serve
    from test_support import FIXTURES
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    url = "https://docs.example.com/sample.pdf"
    assert cli(tmp_path, "init", "--url", "https://a.example/")[0] == 0
    serve(monkeypatch, {url: lambda: FakeResponse(body=pdf, headers={"Content-Type": "application/pdf"})})

    code, out, err = cli(tmp_path, "fetch-file", "--url", url, "--name", "sample.pdf")
    assert (code, err) == (0, "")
    result = json.loads(out)
    assert list(result) == ["path", "bytes", "sha256", "content_type", "final_url", "http_status"]
    assert result["bytes"] == len(pdf) and result["http_status"] == 200

    code, out, err = cli(tmp_path, "fetch-file", "--url", url, "--name", "sample.pdf")
    assert code == 2 and "already exists" in out
    assert cli(tmp_path, "fetch-file", "--url", url, "--name", "sample.pdf", "--overwrite")[0] == 0

    code, out, err = cli(tmp_path, "pdf-text", "--name", "sample.pdf")
    assert (code, err) == (0, "")
    assert json.loads(out)["pages"] == 2
    text = tmp_path / "acme" / ".scratch" / "text" / "sample.pdf.txt"
    assert text.read_bytes() == b"=== page 1 ===\nSample page one\n=== page 2 ===\nSample page two\n"
    assert all(p == "acme" or p.startswith("acme" + os.sep) for p in walk(tmp_path))


def test_fetch_file_exit_codes(tmp_path, monkeypatch):
    import email.message
    import urllib.error
    from test_fetch import FakeResponse, serve
    url = "https://docs.example.com/doc.pdf"
    assert cli(tmp_path, "fetch-file", "--url", url, "--name", "doc.pdf")[0] == 3      # no run yet
    assert cli(tmp_path, "init", "--url", "https://a.example/")[0] == 0
    serve(monkeypatch, {
        url: urllib.error.HTTPError(url, 404, "Not Found", email.message.Message(), None),
        "https://docs.example.com/r": FakeResponse(302, headers={"Location": "http://docs.example.com/doc.pdf"}),
    })
    code, out, _ = cli(tmp_path, "fetch-file", "--url", "http://docs.example.com/doc.pdf", "--name", "doc.pdf")
    assert code == 2 and out == "url: scheme must be https\n"
    assert cli(tmp_path, "fetch-file", "--url", "https://localhost/doc.pdf", "--name", "doc.pdf")[0] == 2
    assert cli(tmp_path, "fetch-file", "--url", url, "--name", "../doc.pdf")[0] == 2
    code, out, err = cli(tmp_path, "fetch-file", "--url", url, "--name", "doc.pdf")
    assert (code, out) == (4, "") and err == "network error: HTTP 404 Not Found for %s\n" % url
    code, out, err = cli(tmp_path, "fetch-file", "--url", "https://docs.example.com/r", "--name", "doc.pdf")
    assert code == 4 and "refused: scheme must be https" in err


def test_pdf_text_exit_codes(tmp_path, monkeypatch):
    import shutil
    import sys
    from test_support import FIXTURES
    from lib import pdftext
    assert cli(tmp_path, "init", "--url", "https://a.example/")[0] == 0
    assert cli(tmp_path, "pdf-text", "--name", "absent.pdf")[0] == 2
    shutil.copyfile(FIXTURES / "sample.pdf", tmp_path / "acme" / ".scratch" / "raw" / "sample.pdf")
    monkeypatch.setitem(sys.modules, "pypdf", None)
    code, out, err = cli(tmp_path, "pdf-text", "--name", "sample.pdf")
    v = pdftext.PYPDF_VERSION
    assert (code, out) == (4, "")
    assert err == "dependency error: pypdf %s required: python -m pip install --user pypdf==%s\n" % (v, v)

# v0.4.1 amend --------------------------------------------------------------------------------------------

@pytest.mark.d2
@NEEDS_D2
def test_amend_cli(tmp_path):
    project = _ready(tmp_path)
    assert cli(tmp_path, "finalize")[0] == 0
    good = project.scratch / "logs" / "amend-1.txt"
    good.write_bytes(b"note missed upgrades\n")
    bad = project.scratch / "logs" / "amend-bad.txt"
    bad.write_bytes(b"note x\naccept N1\n")
    code, out, _ = cli(tmp_path, "amend", "--file", str(bad))
    assert (code, out) == (2, "line 2: accept is not allowed in an amendment\n")
    code, out, err = cli(tmp_path, "amend", "--file", str(good))
    assert (code, err) == (0, "")
    result = json.loads(out)
    assert list(result) == ["amendment", "round", "phase", "archived_to", "commands"]
    assert (result["amendment"], result["round"], result["phase"], result["commands"]) == (1, 2, "research", 1)
    code, _, err = cli(tmp_path, "amend", "--file", str(good))
    assert code == 3 and "amend requires a final run (current phase: research)" in err
