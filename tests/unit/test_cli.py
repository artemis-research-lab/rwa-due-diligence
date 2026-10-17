"""Test group 10: end-to-end through the CLI in a temporary reports root."""

import json
import os
from pathlib import Path

from test_support import load_fixture, merge_fixture_body, run_cli, source_argv, walk
from lib import runstate


def cli(root, *argv):
    return run_cli(list(argv[:1]) + ["--slug", "acme", "--root", str(root)] + list(argv[1:]))


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
    assert [Path(p).name for p in result["outputs"]] == ["acme.dd.json", "acme.report.md", "acme.report.html"]
    for p in result["outputs"] + [result["audit_dir"], result["scratch_dir"]]:
        assert os.path.exists(p) and base in Path(p).resolve().parents

    final = json.loads(Path(result["outputs"][0]).read_bytes().decode("utf-8"))
    assert final["run"]["status"] == "final" and final["run"]["round"] == 2
    report = Path(result["outputs"][1]).read_bytes().decode("utf-8")
    assert "### Round 1\n\n```text\naccept N1\n```" in report
    assert "### Round 2\n\n```text\nnote good enough\nfinalize\n```" in report
    assert "DRAFT" not in report
    page = Path(result["outputs"][2]).read_bytes().decode("utf-8")
    assert '<pre class="dd-pre">note good enough\nfinalize</pre>' in page
    assert "DRAFT" not in page

    # Nothing was created outside <tmp>/acme.
    assert before == []
    assert all(p == "acme" or p.startswith("acme" + os.sep) for p in walk(tmp_path))


def test_exit_codes(tmp_path):
    assert cli(tmp_path, "validate")[0] == 3            # no run yet
    assert run_cli(["init", "--slug", "../x", "--url", "u", "--root", str(tmp_path)])[0] == 3
    assert cli(tmp_path, "init", "--url", "https://a.example/")[0] == 0
    code, out, _ = cli(tmp_path, "validate")
    assert code == 2 and out == ("project.products[0]: P1 has no flow edge\n"
                                 "project.products[0]: P1 has no yield entry\n")
    assert cli(tmp_path, "review")[0] == 2
    assert cli(tmp_path, "finalize")[0] == 3
    code, _, err = cli(tmp_path, "init", "--url", "https://a.example/")
    assert code == 3 and 'run exists (phase research); use "dd.py status" to inspect or --new-run' in err


def test_render_writes_draft_html(tmp_path):
    assert cli(tmp_path, "init", "--url", "https://a.example/")[0] == 0
    code, out, _ = cli(tmp_path, "render")
    assert code == 0
    draft = tmp_path / "acme" / ".scratch" / "draft"
    assert (draft / "acme.report.md").is_file() and (draft / "acme.report.html").is_file()
    assert '<p class="dd-banner dd-banner--draft">' in (draft / "acme.report.html").read_bytes().decode("utf-8")


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
    for name in ("init", "add-source", "validate", "review", "directives", "render", "status", "finalize",
                 "schema-doc"):
        assert name in buf.getvalue()
