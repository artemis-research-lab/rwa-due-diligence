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

# v0.4.1 amendments ---------------------------------------------------------------------------------------

def amend_errors(text):
    with pytest.raises(directives.DirectiveError) as exc:
        directives.parse_amendment(text, DOC)
    return exc.value.errors


def test_amend_commands_constant():
    assert directives.AMEND_COMMANDS == ("note", "add-source", "answer", "drop")


def test_parse_amendment_accepts_allowed_commands():
    text = ("note sUSDai upgrades missed\nadd-source https://x.example/safe : Safe history\n"
            "answer G1 : see Safe history | drop D1 : superseded")
    assert directives.parse_amendment(text, DOC) == [
        {"cmd": "note", "text": "sUSDai upgrades missed", "line": 1},
        {"cmd": "add-source", "target": "https://x.example/safe", "why": "Safe history", "line": 2},
        {"cmd": "answer", "id": "G1", "text": "see Safe history", "line": 3},
        {"cmd": "drop", "id": "D1", "reason": "superseded", "line": 3},
    ]


@pytest.mark.parametrize("line, name", [("accept N1", "accept"), ("reject N1", "reject"),
                                        ("priority N1", "priority"), ("limit N1 5", "limit"),
                                        ("allow-fallback N1 archive", "allow-fallback"),
                                        ("finalize", "finalize")])
def test_parse_amendment_rejects_other_commands(line, name):
    assert amend_errors("note x\n" + line) == ["line 2: %s is not allowed in an amendment" % name]


def test_parse_amendment_requires_a_note():
    assert amend_errors("drop D1 : superseded") == ["line 0: an amendment needs at least one note"]
    assert amend_errors("") == ["line 0: an amendment needs at least one note"]


def test_parse_amendment_unknown_id():
    assert amend_errors("note x\nanswer G99 : y") == ["line 2: unknown id G99"]


# v0.7.0 ----------------------------------------------------------------------------------------------------

def test_answer_and_drop_accept_u_and_r_ids():
    doc = dict(DOC, findings=DOC["findings"] + [dict(DOC["findings"][6], id="U3")])
    assert directives.parse("answer U3 : covered by the 2026 policy\ndrop R1 : reconciled by the issuer\n", doc) == [
        {"cmd": "answer", "id": "U3", "text": "covered by the 2026 policy", "line": 1},
        {"cmd": "drop", "id": "R1", "reason": "reconciled by the issuer", "line": 2}]
    assert errors("answer U9 : x") == ["line 1: unknown id U9"]
    assert errors("drop C1 : x") == ["line 1: not a directive: drop C1 : x"]
