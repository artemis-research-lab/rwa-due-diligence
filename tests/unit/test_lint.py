"""v0.4.2: address lint (lib/lint.py, dd.py lint)."""

import json

from test_support import build_run, run_cli
from lib import lint

LOWER = "0x" + "ab" * 20
UPPER = "0x" + "AB" * 20
MIXED = "0x" + "aB" * 20
DIGITS = "0x" + "12" * 20


def _doc(**extra):
    doc = {"run": {"slug": "x"}, "onchain": {"contracts": [{"address": None, "proxy": {"value": None}}]},
           "sources": [{"url": "https://e.example/" + LOWER, "excerpt": UPPER}]}
    doc.update(extra)
    return doc


def test_lower_and_upper_warned():
    doc = _doc()
    doc["onchain"]["contracts"][0]["address"] = LOWER
    doc["onchain"]["contracts"][0]["proxy"]["value"] = "impl " + UPPER + "."
    assert lint.address_warnings(doc) == [
        {"path": "onchain.contracts[0].address", "address": LOWER},
        {"path": "onchain.contracts[0].proxy.value", "address": UPPER}]


def test_mixed_case_and_digit_only_not_warned():
    doc = _doc()
    doc["onchain"]["contracts"][0]["address"] = MIXED
    doc["onchain"]["contracts"][0]["proxy"]["value"] = DIGITS
    assert lint.address_warnings(doc) == []


def test_longer_hex_not_an_address():
    doc = _doc(history=[{"change": LOWER + "c"}, {"change": "x" + LOWER}])
    assert lint.address_warnings(doc) == [{"path": "history[1].change", "address": LOWER}]


def test_sources_ignored():
    assert lint.address_warnings(_doc()) == []


def test_sorted_and_deduplicated():
    doc = _doc(findings=[{"statement": "%s and %s and %s" % (UPPER, LOWER, LOWER)}],
               entities=[{"note": LOWER}])
    assert lint.address_warnings(doc) == [
        {"path": "entities[0].note", "address": LOWER},
        {"path": "findings[0].statement", "address": UPPER},
        {"path": "findings[0].statement", "address": LOWER}]


def test_cli_lint(tmp_path):
    project = build_run(tmp_path)
    before = project.work_file.read_bytes()
    doc = json.loads(before.decode("utf-8"))
    code, out, err = run_cli(["lint", "--slug", "acme", "--root", str(tmp_path)])
    assert (code, err) == (0, "")
    assert out == json.dumps({"address_warnings": lint.address_warnings(doc)}, indent=2) + "\n"
    assert {"path": "flows.nodes[1].ref", "address": "0x" + "0" * 38 + "a1"} in json.loads(out)["address_warnings"]
    assert project.work_file.read_bytes() == before
    doc["onchain"]["contracts"][0]["address"] = MIXED
    project.work_file.write_bytes(json.dumps(doc).encode("utf-8"))
    code, out, _ = run_cli(["lint", "--slug", "acme", "--root", str(tmp_path)])
    assert code == 0
    assert {"path": "onchain.contracts[0].address", "address": MIXED} not in json.loads(out)["address_warnings"]


def test_cli_lint_exit_codes(tmp_path):
    code, _, err = run_cli(["lint", "--slug", "nope", "--root", str(tmp_path)])
    assert code == 3 and "no run for slug nope" in err
    project = build_run(tmp_path)
    project.work_file.write_bytes(b"{not json")
    assert run_cli(["lint", "--slug", "acme", "--root", str(tmp_path)])[0] == 2