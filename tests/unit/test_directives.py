"""Test group 7: directive grammar."""

import pytest

from test_support import build_run, load_fixture
from lib import directives, runstate

DOC = load_fixture()


def parse(text):
    return directives.parse(text, DOC)


def errors(text):
    with pytest.raises(directives.DirectiveError) as exc:
        parse(text)
    return exc.value.errors


def test_every_form_parses():
    text = "\n".join([
        "# comment",
        "",
        "accept N1 | reject N2",
        "add-source https://x.example/a.pdf : registry filing",
        "answer G1 : statements requested from the issuer",
        "drop D1 : fee confirmed by phone",
        "note look harder at custody",
        "priority N2, N1",
        "limit N1 5",
        "allow-fallback N2 archive | allow-fallback N1 browser",
    ])
    assert parse(text) == [
        {"cmd": "accept", "id": "N1", "line": 3},
        {"cmd": "reject", "id": "N2", "line": 3},
        {"cmd": "add-source", "target": "https://x.example/a.pdf", "why": "registry filing", "line": 4},
        {"cmd": "answer", "id": "G1", "text": "statements requested from the issuer", "line": 5},
        {"cmd": "drop", "id": "D1", "reason": "fee confirmed by phone", "line": 6},
        {"cmd": "note", "text": "look harder at custody", "line": 7},
        {"cmd": "priority", "ids": ["N2", "N1"], "line": 8},
        {"cmd": "limit", "id": "N1", "calls": 5, "line": 9},
        {"cmd": "allow-fallback", "id": "N2", "mode": "archive", "line": 10},
        {"cmd": "allow-fallback", "id": "N1", "mode": "browser", "line": 10},
    ]
    assert parse("finalize\n") == [{"cmd": "finalize", "line": 1}]
    assert parse("note wrap up\r\nfinalize | reject N1\r\n")[1] == {"cmd": "finalize", "line": 2}


def test_unknown_command():
    assert errors("accept N1\nplease do more\n") == ["line 2: not a directive: please do more"]


def test_case_sensitive():
    assert errors("Accept N1") == ["line 1: not a directive: Accept N1"]


def test_bad_id():
    assert errors("accept N9") == ["line 1: unknown id N9"]
    assert errors("\n\nanswer D7 : x") == ["line 3: unknown id D7"]
    assert errors("answer C1 : x") == ["line 1: not a directive: answer C1 : x"]


def test_limit_out_of_range():
    assert errors("limit N1 0") == ["line 1: limit calls must be 1..20"]
    assert errors("limit N1 21") == ["line 1: limit calls must be 1..20"]


def test_finalize_mixed_with_accept():
    assert errors("accept N1\nfinalize") == [
        "line 2: finalize cannot be combined with accept/add-source/answer (line 1)"]


def test_empty_file_and_empty_command():
    assert errors("# only comments\n\n") == ["line 0: no directives found"]
    assert errors("accept N1 |") == ["line 1: empty command"]


def test_nothing_written_on_error(tmp_path):
    project = build_run(tmp_path)
    runstate.make_review(tmp_path, "acme")
    before = runstate.load_state(project)
    work_before = project.work_file.read_bytes()
    reply = project.scratch / "logs" / "bad.txt"
    reply.write_bytes(b"accept N1\nlimit N1 0\n")
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.apply_directives(tmp_path, "acme", reply)
    assert exc.value.errors == ["line 2: limit calls must be 1..20"]
    assert not (project.round_dir(1) / "directives.txt").exists()
    assert not (project.round_dir(1) / "directives.json").exists()
    assert runstate.load_state(project) == before
    assert project.work_file.read_bytes() == work_before
