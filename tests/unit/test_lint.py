"""v0.4.2 address lint, v0.6.0 layer, claim and path lint and v0.7.0 amount and provenance lint (lib/lint.py,
dd.py lint)."""

import copy
import json

from test_support import build_run, claim, load_fixture, run_cli
from lib import lint

KEYS = ["address_warnings", "layer_warnings", "claim_warnings", "path_warnings", "amount_warnings",
        "provenance_warnings"]
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
    assert out == json.dumps(lint.lint(doc), indent=2) + "\n"
    assert list(json.loads(out)) == KEYS
    assert json.loads(out) == {key: [] for key in KEYS}  # the fixture uses digit-only fake addresses
    assert project.work_file.read_bytes() == before
    doc["flows"]["nodes"][1]["ref"] = LOWER
    project.work_file.write_bytes(json.dumps(doc).encode("utf-8"))
    code, out, _ = run_cli(["lint", "--slug", "acme", "--root", str(tmp_path)])
    assert {"path": "flows.nodes[1].ref", "address": LOWER} in json.loads(out)["address_warnings"]
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
    doc = load_fixture()
    del doc["supports"]
    project.work_file.write_bytes(json.dumps(doc).encode("utf-8"))
    code, out, _ = run_cli(["lint", "--slug", "acme", "--root", str(tmp_path)])
    assert (code, out) == (2, '(root): missing key "supports"\n')


# --------------------------------------------------------------------------- v0.6.0 section 2.3

def _x(doc, xid):
    return next(x for x in doc["interfaces"] if x["id"] == xid)


def test_fixture_has_no_warnings():
    assert lint.lint(load_fixture()) == {key: [] for key in KEYS}


def test_layer_warning_within_l2():
    doc = load_fixture()
    x7 = _x(doc, "X7")
    x7.update({"kind": "within_L2", "method": claim()})
    x7["to"] = "E4"
    assert lint.layer_warnings(doc) == [
        {"path": "interfaces[6]", "message": "X7: within_L2 but E4 has no L2 function for T2"}]
    x7["from"] = "E5"  # E5 has an L2 function only for T1
    assert lint.layer_warnings(doc) == [
        {"path": "interfaces[6]", "message": "X7: within_L2 but E5 has no L2 function for T2"},
        {"path": "interfaces[6]", "message": "X7: within_L2 but E4 has no L2 function for T2"}]


def test_layer_warning_each_layered_kind():
    doc = load_fixture()
    for e in doc["entities"]:
        e["functions"] = []
    messages = sorted(w["message"] for w in lint.layer_warnings(doc))
    assert "X1: holder_L1 but E1 has no L1 function for T1" in messages
    assert "X2: L1_L2 but E1 has no L1 function for T1" in messages and "X2: L1_L2 but E5 has no L2 function for T1" \
        in messages
    assert "X4: L2_L3 but E6 has no L2 function for T1" in messages
    assert "X8: L3_L3O but E10 has no L3-O function for T1" in messages
    assert "X9: sleeve_holding but E1 has no L1 function for T3" in messages
    assert not any(m.startswith(("X10:", "X13:")) for m in messages)  # look-through and asset sale unchecked
    assert not any(m.startswith("X1: holder_L1 but P1") for m in messages)


def test_layer_l2_l3_from_l1_with_l2_function_is_fine():
    doc = load_fixture()
    assert _x(doc, "X7")["from"] == "E1"
    assert not [w for w in lint.layer_warnings(doc) if w["message"].startswith("X7")]
    doc["entities"][0]["functions"] = [fn for fn in doc["entities"][0]["functions"] if fn["layer"] != "L2"]
    assert [w["message"] for w in lint.layer_warnings(doc)] == [
        "X7: L2_L3 but E1 has no L2 function for T2", "X11: L2_L3 but E1 has no L2 function for T2",
        "X12: L2_L3 but E1 has no L2 function for T2"]


def _pool(doc, legal_class, evidence):
    x2 = _x(doc, "X2")
    x2["route"]["value"] = "POOL"
    x2["legal_class"].update({"value": legal_class, "evidence": evidence})
    return doc


def test_claim_warning_pool_with_loan_class_needs_legal_doc():
    doc = _pool(load_fixture(), "AP", ["S1"])
    assert lint.claim_warnings(doc) == [{
        "path": "interfaces[1].legal_class",
        "message": "X2: POOL with legal class AP needs a contract (legal_doc) source; use PROTOCOL_ENTITLEMENT or "
                   "leave it not_found"}]
    assert lint.claim_warnings(_pool(load_fixture(), "AP", ["S1", "S8"])) == []  # S8 is a legal_doc
    assert lint.claim_warnings(_pool(load_fixture(), "PROTOCOL_ENTITLEMENT", ["S1"])) == []
    assert lint.claim_warnings(_pool(load_fixture(), None, [])) == []
    for code in ("DL", "DI", "PI"):
        assert len(lint.claim_warnings(_pool(load_fixture(), code, ["S4"]))) == 1


def test_path_warnings():
    doc = load_fixture()
    doc["interfaces"] = [x for x in doc["interfaces"] if x["kind"] not in ("holder_L1", "sleeve_holding")]
    assert lint.path_warnings(doc) == [
        {"path": "strategies[0]", "message": "T1: no holder_L1 interface"},
        {"path": "strategies[1]", "message": "T2: no holder_L1 interface"},
        {"path": "strategies[2]", "message": "T3: no sleeve_holding interface"}]
    doc = load_fixture()
    doc["interfaces"] = [x for x in doc["interfaces"] if x["kind"] == "holder_L1"]
    doc["strategies"][1]["component"] = "DEFI_LENDING"
    assert [w["message"] for w in lint.path_warnings(doc)] == [
        "T1: no L1_L2 interface", "T1: no L2_L3 interface", "T2: no L1_L2 interface", "T2: no L2_L3 interface",
        "T3: no sleeve_holding interface"]


def test_path_l1_to_l2_l3_counts_as_l1_l2():
    doc = load_fixture()
    assert not any(x["kind"] == "L1_L2" and x["strategy"] == "T2" for x in doc["interfaces"])
    assert lint.path_warnings(doc) == []
    doc["entities"][0]["functions"] = [fn for fn in doc["entities"][0]["functions"] if fn["layer"] != "L1"]
    assert lint.path_warnings(doc) == [{"path": "strategies[1]", "message": "T2: no L1_L2 interface"}]


def test_lint_is_sorted_and_deterministic():
    doc = load_fixture()
    for e in doc["entities"]:
        e["functions"] = []
    first = lint.lint(copy.deepcopy(doc))
    assert first == lint.lint(doc)
    for key in KEYS[1:]:
        assert first[key] == sorted(first[key], key=lambda w: (w["path"], w["message"]))


# --------------------------------------------------------------------------- v0.7.0 section 2.3

def _amount(doc, xid, j=0):
    return _x(doc, xid)["amounts"][j]


def test_amount_warning_onchain_without_block_or_chain():
    doc = load_fixture()
    _amount(doc, "X2")["block"] = None
    assert lint.amount_warnings(doc) == [{"path": "interfaces[1].amounts[0]",
                                          "message": "X2.amounts[0]: on-chain amount without block and chain"}]
    _amount(doc, "X2").update({"block": 1, "chain": None})
    assert len(lint.amount_warnings(doc)) == 1
    _amount(doc, "X2")["value"]["evidence"] = ["S8"]
    assert lint.amount_warnings(doc) == []


def test_amount_warning_no_observation_time():
    doc = load_fixture()  # test-local copy: the shared fixture lints clean
    x2 = _x(doc, "X2")
    x2["amounts"].append(dict(copy.deepcopy(x2["amounts"][1]), basis="CURRENT_BALANCE", as_of=None,
                              valuation_basis=None))
    assert lint.amount_warnings(doc) == [{"path": "interfaces[1].amounts[3]",
                                          "message": "X2.amounts[3]: no observation time; it will not be counted"}]


def test_amount_warning_no_countable_basis():
    doc = load_fixture()
    _amount(doc, "X9")["basis"] = "OTHER"
    _amount(doc, "X9")["scope"] = "Stablecoin held by E1 in the treasury sleeve"
    assert lint.amount_warnings(doc) == [{"path": "interfaces[8]", "message": "X9: no countable basis "
                                                                             "(CURRENT_BALANCE, POSITION_VALUE, "
                                                                             "OUTSTANDING_PRINCIPAL)"}]
    _x(doc, "X9")["amounts"] = []
    assert lint.amount_warnings(doc) == []


def test_amount_warning_cumulative_period():
    doc = load_fixture()
    _amount(doc, "X2", 2)["scope"] = "AUP loan sample of twelve loans"
    assert lint.amount_warnings(doc) == [{"path": "interfaces[1].amounts[2]",
                                          "message": "X2.amounts[2]: CUMULATIVE_FUNDED scope should state the period"}]
    _amount(doc, "X2", 2)["scope"] = "AUP loan sample, first half 12026"
    assert len(lint.amount_warnings(doc)) == 1  # a five-digit run is not a year


def test_provenance_warning():
    doc = load_fixture()
    _amount(doc, "X2", 2)["value"].update({"origin": None, "assurance": None, "evidence": ["S8", "S9"]})
    assert lint.provenance_warnings(doc) == [{
        "path": "interfaces[1].amounts[2].value",
        "message": "X2.amounts[2].value: cites an auditor source; set origin and assurance (curator Q8)"}]
    doc["entities"][2]["jurisdiction"]["evidence"] = ["S8", "S9"]  # not_found: no warning
    assert len(lint.provenance_warnings(doc)) == 1


def test_provenance_warning_legal_character_through_auditor_procedure():
    doc = load_fixture()
    x5 = _x(doc, "X5")
    x5["legal_class"] = claim("DL", "verified", ["S9"], origin="auditor_procedure", assurance="TESTED")
    assert lint.provenance_warnings(doc) == [{
        "path": "interfaces[4].legal_class",
        "message": "X5.legal_class: an auditor procedure shows the documents were inspected, not their legal effect "
                   "(curator Q8); take origin from the source that states the legal character"}]
    x5["legal_class"] = claim("DL", "verified", ["S2", "S9"], origin="regulator", assurance="NOT_TESTED")
    assert lint.provenance_warnings(doc) == []
    doc["holder_rights"][0]["look_through"] = claim("none", "verified", ["S9"], origin="auditor_procedure",
                                                    assurance="TESTED")
    assert [w["message"][:30] for w in lint.provenance_warnings(doc)] == ["P1.holder_rights.look_through:"]


def test_claim_warning_deployment_not_set():
    doc = load_fixture()
    doc["strategies"][1]["deployment"] = claim()
    assert lint.claim_warnings(doc) == [{"path": "strategies[1].deployment",
                                         "message": "T2.deployment: not set for a credit strategy"}]
    doc["strategies"][1]["deployment"] = claim(None, "not_found", ["S7"], note="Not disclosed.")
    assert lint.claim_warnings(doc) == []
    doc["strategies"][2]["deployment"] = claim()  # LIQUIDITY_SLEEVE: no warning
    assert lint.claim_warnings(doc) == []


def test_path_warning_blocking_finding_unplaced():
    doc = load_fixture()
    doc["findings"][2].update({"k_checks": [], "impact": []})
    assert lint.path_warnings(doc) == [{
        "path": "findings[2]", "message": "G3: blocking finding without k_checks or impact (section 1 cannot "
                                          "place it)"}]
    doc["findings"][2]["material"] = True
    assert lint.path_warnings(doc) == []
