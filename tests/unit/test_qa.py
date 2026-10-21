"""v0.7.0 section 6, v0.7.1, v0.7.2: quantitative and provenance checks QA1-QA13 and analyst expectations
(lib/qa.py)."""

import json

import pytest

from test_support import FIXTURES, load_fixture
from lib import claims, framework, qa, schema

IDS = ["QA%d" % i for i in range(1, 14)]
RESULT_KEYS = {"id", "rule", "result", "detail", "target", "legacy", "mapping"}


def _results(doc, expectations=None):
    return {r["id"]: r for r in qa.run(doc, expectations)}


def _detail(doc, rule):
    result = _results(doc)[rule]
    assert result["result"] == "fail", result
    return result["detail"]


def _one_measure_off(monkeypatch):
    """Switch off the one-measure-per-edge rule (D78)."""
    monkeypatch.setattr(framework, "_one_measure", lambda x, reasons: reasons)


def _count_also(monkeypatch, xid):
    """Break the counting rule for one interface so the QA rules have something to catch."""
    original = framework._reason
    monkeypatch.setattr(framework, "_reason", lambda x, a: "counted" if x["id"] == xid else original(x, a))
    _one_measure_off(monkeypatch)


def test_fixture_passes_every_rule():
    results = qa.run(load_fixture())
    assert [r["id"] for r in results] == IDS
    assert [r["rule"] for r in results] == [name for _, name, _ in schema.QA_RULES]
    assert {r["result"] for r in results} == {"pass"} and qa.failed(results) == []
    assert results[3]["detail"] == "ok; unverified: X13.amounts[0]"
    assert all(r["detail"] == "ok" for i, r in enumerate(results) if i != 3)


def test_qa1_basis(monkeypatch):
    original = framework.allocation_totals

    def merged(doc):
        totals = original(doc)
        first, = totals["strategies"]["T1"]
        totals["strategies"]["T1"] = [dict(first, sum=first["sum"] + 1)]
        return totals
    monkeypatch.setattr(framework, "allocation_totals", merged)
    assert _detail(load_fixture(), "QA1") == "T1"


def test_qa1_duplicate_key(monkeypatch):
    original = framework.allocation_totals

    def doubled(doc):
        totals = original(doc)
        totals["products"]["P2"] = totals["products"]["P2"] * 2
        return totals
    monkeypatch.setattr(framework, "allocation_totals", doubled)
    assert _detail(load_fixture(), "QA1") == "P2"


def test_qa2_lookthrough(monkeypatch):
    _count_also(monkeypatch, "X10")
    assert _detail(load_fixture(), "QA2") == "X10.amounts[0]"


def test_qa3_alternative(monkeypatch):
    doc = load_fixture()
    doc["interfaces"][8]["alternative"] = {"group": "A2", "option": "a"}
    assert _results(doc)["QA3"]["result"] == "pass"  # the counting rule leaves it out
    _count_also(monkeypatch, "X9")
    assert _detail(doc, "QA3") == "X9.amounts[0]"


def test_qa4_proceeds(monkeypatch):
    doc = load_fixture()
    doc["interfaces"][12]["amounts"][0]["value"]["status"] = "verified"
    assert _results(doc)["QA4"] == {"id": "QA4", "rule": "proceeds", "result": "pass", "detail": "ok",
                                    "target": None, "legacy": None, "mapping": ""}
    _count_also(monkeypatch, "X13")
    assert _detail(load_fixture(), "QA4") == "X13.amounts[0]"


def test_qa5_asof(monkeypatch):
    doc = load_fixture()
    doc["interfaces"][8]["amounts"][0]["as_of"] = None
    _count_also(monkeypatch, "X9")
    assert _detail(doc, "QA5") == "X9.amounts[0]"


def test_qa6_stockflow(monkeypatch):
    _count_also(monkeypatch, "X2")
    assert _detail(load_fixture(), "QA6") == "CORE_CREDIT, P1, T1, X2.amounts[2]"


def test_qa7_provenance():
    doc = load_fixture()
    doc["interfaces"][1]["amounts"][1]["value"]["evidence"] = ["S8", "S9"]
    assert _detail(doc, "QA7") == "X2.amounts[1].value"
    doc = load_fixture()
    doc["interfaces"][1]["amounts"][2]["value"]["status"] = "third_party_reported"
    assert _detail(doc, "QA7") == "X2.amounts[2].value"
    doc = load_fixture()
    doc["strategies"][0]["l3_business"]["performance"]["assurance"] = "NOT_TESTED"  # P4: verified needs TESTED
    assert _detail(doc, "QA7") == "T1.l3_business.performance"


def test_qa7_reuses_the_claim_combination_rules():
    doc = load_fixture()
    perf = doc["strategies"][0]["l3_business"]["performance"]
    perf["status"] = "third_party_reported"  # P4: auditor_procedure TESTED requires verified
    assert claims.provenance_errors(("strategies", 0, "l3_business", "performance"), perf, ["auditor"]) == [
        "strategies[0].l3_business.performance: origin auditor_procedure with assurance TESTED requires status "
        "verified"]
    assert _detail(doc, "QA7") == "T1.l3_business.performance"


def test_qa8_conflicts():
    doc = load_fixture()
    doc["findings"][3]["assertions"].pop()
    assert _detail(doc, "QA8") == "X6.terms"
    doc = load_fixture()
    doc["findings"][6]["subjects"].append("X6.terms")
    assert _detail(doc, "QA8") == "X6.terms"


def test_qa9_placeholder():
    doc = load_fixture()
    doc["findings"][4]["scope_note"] = schema.MIGRATED_SCOPE_NOTE
    doc["interfaces"][3]["amounts"][1]["scope"] = schema.MIGRATED_AMOUNT_SCOPE
    assert _detail(doc, "QA9") == "D2, X4.amounts[1]"


def test_qa10_section1(monkeypatch):
    monkeypatch.setattr(framework, "critical", lambda doc: ["G1"])
    assert _detail(load_fixture(), "QA10") == "G3, R1"


def test_qa11_deployment():
    doc = load_fixture()
    doc["strategies"][1]["deployment"]["value"] = "DEPLOYED_VERIFIED"
    assert _detail(doc, "QA11") == "T2"
    doc["strategies"][1]["component"] = "LIQUIDITY_SLEEVE"
    assert _results(doc)["QA11"]["result"] == "pass"


def test_qa12_onemeasure(monkeypatch):
    assert _results(load_fixture())["QA12"] == {"id": "QA12", "rule": "onemeasure", "result": "pass",
                                                 "detail": "ok", "target": None, "legacy": None, "mapping": ""}
    _one_measure_off(monkeypatch)
    assert _detail(load_fixture(), "QA12") == "X2"


def test_qa13_timebasis_retrieval_time():
    assert _results(load_fixture())["QA13"] == {"id": "QA13", "rule": "timebasis", "result": "pass",
                                                 "detail": "ok", "target": None, "legacy": None, "mapping": ""}
    doc = load_fixture()
    doc["interfaces"][1]["amounts"][1]["as_of"] = "2026-10-01T08:40:00Z"  # the retrieval time of S8
    assert _detail(doc, "QA13") == "X2.amounts[1]"
    doc["interfaces"][1]["amounts"][1].update(block=20871240, chain="ethereum")  # a block read keeps its time
    assert _results(doc)["QA13"]["result"] == "pass"


def test_qa13_timebasis_counted_unresolved(monkeypatch):
    doc = load_fixture()
    doc["interfaces"][8]["amounts"][0]["as_of"] = None
    assert _results(doc)["QA13"]["result"] == "pass"  # the counting rule leaves it out
    _count_also(monkeypatch, "X9")
    assert _detail(doc, "QA13") == "X9.amounts[0]"


# --------------------------------------------------------------------------- expectations

def _entry(path, op, value, ident="e1"):
    return {"id": ident, "case": "case %s" % ident, "path": path, "op": op, "value": value}


@pytest.mark.parametrize("path, op, good, bad", [
    ("X2.amounts[0].basis", "equals", "CURRENT_BALANCE", "POSITION_VALUE"),
    ("X2.amounts[0].value", "equals", 25000000, 1),
    ("T2.deployment", "in", ["DISCLOSED_UNVERIFIED", "UNRESOLVED"], ["DEPLOYED_VERIFIED"]),
    ("X2.amounts[2].value", "status", "self_reported", "verified"),
    ("X6.terms", "flag", "CONFLICTING", "SELF_REPORTED"),
    ("X4.security", "flag", "SELF_REPORTED", "CONFLICTING"),
    ("X2.amounts[0]", "counted", True, False),
    ("X2.amounts[1]", "counted", False, True),
    ("X13.amounts[0]", "counted", False, True),
    ("X13.loan_identity", "exists", True, False),
    ("X13.amounts[5]", "exists", False, True),
    ("@G3.statement", "not_contains", "Misconduct", "independent review"),
    ("@G3", "exists", True, False),
])
def test_each_op_passes_and_fails(path, op, good, bad):
    doc = load_fixture()
    passed = qa.check_expectation(doc, _entry(path, op, good))
    failed = qa.check_expectation(doc, _entry(path, op, bad))
    assert passed["result"] == "pass" and failed["result"] == "fail", (passed, failed)
    assert passed["id"] == "E:e1" and passed["rule"] == "case e1"
    target = "R1" if path.startswith("@G3") else path.split(".")[0].split("[")[0]
    assert passed["target"] == failed["target"] == target
    assert failed["detail"].startswith("%s: %s %s %s -> " % (target, path, op, json.dumps(bad, sort_keys=True)))


def test_expectation_detail_and_missing_paths():
    doc = load_fixture()
    assert qa.check_expectation(doc, _entry("X2.amounts[0].unit", "equals", "USD"))["detail"] == \
        'X2: X2.amounts[0].unit equals "USD" -> "USDC"'
    missing = qa.check_expectation(doc, _entry("X99.terms", "exists", True))
    assert (missing["target"], missing["legacy"], missing["mapping"]) == (None, None, "")
    assert missing["detail"] == "unresolved: X99.terms exists true -> false"
    legacy = qa.check_expectation(doc, _entry("@G9.type", "exists", True))
    assert (legacy["target"], legacy["legacy"], legacy["result"]) == (None, "G9", "fail")
    for entry in (_entry("X99.terms", "equals", 1), _entry("X2.amounts", "status", "verified"),
                  _entry("X2.terms", "counted", True), _entry("X2", "flag", "CONFIRMED")):
        result = qa.check_expectation(doc, entry)
        assert result["result"] == "fail" and result["detail"].endswith(" -> missing"), entry


def test_fixture_expectations_pass_and_append_after_qa13():
    doc = load_fixture()
    entries = qa.parse_expectations((FIXTURES / "acme.qa-expect.json").read_bytes().decode("utf-8"))
    ops = {e["op"] for e in entries}
    assert ops == set(schema.EXPECT_OPS) and any(e["path"].startswith("@") for e in entries) and len(entries) >= 6
    assert all(e["target"] == "R1" for e in entries if e["path"].startswith("@"))
    assert any(e["path"].startswith("R1.") for e in entries)  # a plain path on a carried-over finding
    results = qa.run(doc, entries)
    assert [r["id"] for r in results] == IDS + ["E:" + e["id"] for e in entries]
    assert qa.failed(results) == []
    assert {frozenset(r) for r in results} == {frozenset(RESULT_KEYS)}
    by_id = {r["id"]: r for r in results}
    assert by_id["E:g3-retyped"]["mapping"] == ("legacy G3 -> R1 (carried_from G3); current G3 is a different"
                                                " finding (carried_from none)")
    assert by_id["E:r1-carried"]["mapping"] == "R1 carried_from G3"
    assert by_id["E:x2-balance-basis"]["mapping"] == ""
    doc["interfaces"][1]["amounts"][0]["basis"] = "POSITION_VALUE"
    assert qa.failed(qa.run(doc, entries)) == ["E:x2-balance-basis"]


def test_target_mismatch_fails():
    doc = load_fixture()
    entries = qa.parse_expectations((FIXTURES / "acme.qa-expect.json").read_bytes().decode("utf-8"))
    wrong = [dict(e, target="G3") if e["id"] == "g3-retyped" else e for e in entries]  # test-local copy
    result = {r["id"]: r for r in qa.run(doc, wrong)}["E:g3-retyped"]
    assert result["result"] == "fail" and result["detail"] == "target mismatch: expected G3, resolved R1"
    assert (result["target"], result["legacy"]) == ("R1", "G3")
    assert qa.check_expectation(doc, dict(_entry("X99.terms", "exists", False), target="X99"))["detail"] == \
        "target mismatch: expected X99, resolved none"


def test_mapping_texts():
    doc = load_fixture()
    entry = dict(_entry("@G3.type", "exists", True), target="R1")
    assert qa.check_expectation(doc, entry)["mapping"] == (
        "legacy G3 -> R1 (carried_from G3); current G3 is a different finding (carried_from none)")
    doc["findings"][2]["carried_from"] = "D9"
    assert qa.check_expectation(doc, entry)["mapping"] == (
        "legacy G3 -> R1 (carried_from G3); current G3 is a different finding (carried_from D9)")
    del doc["findings"][2]  # no current G3
    assert qa.check_expectation(doc, entry)["mapping"] == "legacy G3 -> R1 (carried_from G3)"
    doc = load_fixture()
    assert qa.check_expectation(doc, _entry("R1.type", "exists", True))["mapping"] == "R1 carried_from G3"
    assert qa.check_expectation(doc, _entry("D1.type", "exists", True))["mapping"] == ""  # carried_from = own id
    assert qa.check_expectation(doc, _entry("G3.type", "exists", True))["mapping"] == ""  # new in this run
    assert qa.check_expectation(doc, _entry("X2.terms", "exists", True))["mapping"] == ""
    fallback = qa.check_expectation(doc, dict(_entry("@D1", "exists", True), target="D1"))
    assert (fallback["result"], fallback["mapping"]) == ("pass", "legacy D1 -> D1 (carried_from D1)")


def test_result_keys_identical_for_qa_and_expectations():
    entries = qa.parse_expectations((FIXTURES / "acme.qa-expect.json").read_bytes().decode("utf-8"))
    results = qa.run(load_fixture(), entries)
    assert all(set(r) == RESULT_KEYS for r in results)
    assert [list(r) for r in results[:1]] == [list(r) for r in results[-1:]]


@pytest.mark.parametrize("text, message", [
    ("{not json", "expectations: not valid JSON"),
    ('{"id": "a"}', "expectations: must be a JSON array"),
    ('[1]', "expectations[0]: must be an object"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "equals"}]', "expectations[0]: keys must be id, case, path, op, "
                                                                "value"),
    ('[{"id": "", "case": "c", "path": "X2", "op": "equals", "value": 1}]', "expectations[0].id: must be a string"),
    ('[{"id": "a", "case": "%s", "path": "X2", "op": "equals", "value": 1}]' % ("c" * 121),
     "expectations[0].case: must be a string of at most 120"),
    ('[{"id": "a", "case": "c", "path": "x2", "op": "equals", "value": 1}]', "expectations[0].path: not a resolvable"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "near", "value": 1}]', "expectations[0].op: must be one of"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "in", "value": 1}]', "expectations[0].value: must be a list"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "exists", "value": 1}]',
     "expectations[0].value: must be a boolean"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "flag", "value": 1}]', "expectations[0].value: must be a string"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "exists", "value": true},'
     ' {"id": "a", "case": "c", "path": "X2", "op": "exists", "value": true}]', "expectations[1].id: duplicate id a"),
    ('[{"id": "a", "case": "c", "path": "@G3.type", "op": "exists", "value": true}]',
     "expectations[0].target: required for a legacy (@) path"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "exists", "value": true, "target": "x2"}]',
     "expectations[0].target: must be an id"),
    ('[{"id": "a", "case": "c", "path": "X2", "op": "exists", "value": true, "extra": 1}]',
     "expectations[0]: keys must be id, case, path, op, value, optionally target"),
])
def test_malformed_expectations(text, message):
    with pytest.raises(qa.ExpectationError) as exc:
        qa.parse_expectations(text)
    assert str(exc.value).startswith(message)
