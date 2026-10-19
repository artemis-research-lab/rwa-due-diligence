"""v0.5.0 framework view: subject paths, conflicts, flags, completeness and chain lines."""

import copy

from test_support import load_fixture
from lib import framework, schema


def _discrepancy(doc, subjects):
    doc["findings"].append({"id": "D3", "type": "discrepancy", "topic": "credit", "blocking": False,
                            "statement": "x", "evidence": [], "subjects": subjects})


# --------------------------------------------------------------------------- 3.1

def test_subject_path_examples():
    doc = load_fixture()
    assert framework.subject_path(("interfaces", 3, "security"), doc) == "X4.security"
    assert framework.subject_path(("strategies", 0, "default_path", "loss_waterfall"), doc) == \
        "T1.default_path.loss_waterfall"
    assert framework.subject_path(("entities", 1, "legal_name"), doc) == "E2.legal_name"
    assert framework.subject_path(("entities", 1, "licenses", 0, "regulator"), doc) == "E2.licenses.regulator"
    assert framework.subject_path(("project", "products", 1, "symbol"), doc) == "P2.symbol"
    assert framework.subject_path(("project", "name"), doc) is None
    assert framework.subject_path(("holder_rights", 0, "look_through"), doc) == "P1.holder_rights.look_through"
    assert framework.subject_path(("holder_rights", 1, "look_through"), doc) == "P2.holder_rights.look_through"
    assert framework.subject_path(("flows", "edges", 0, "claim"), doc) is None


def test_holder_rights_subject_conflicts_only_its_product():
    doc = load_fixture()
    doc["findings"] = [f for f in doc["findings"] if f["type"] != "discrepancy"]
    _discrepancy(doc, ["P1.holder_rights.look_through"])
    assert framework.conflicted(doc) == {"P1.holder_rights.look_through"}
    flags = framework.flags(doc)
    assert flags[("holder_rights", 0, "look_through")] == "CONFLICTING"
    assert flags[("holder_rights", 1, "look_through")] != "CONFLICTING"


def test_conflicted_on_fixture():
    assert framework.conflicted(load_fixture()) == {"X4.security"}


def test_conflicted_prefix_at_field_boundary():
    doc = load_fixture()
    doc["findings"] = [f for f in doc["findings"] if f["type"] != "discrepancy"]
    _discrepancy(doc, ["X3.sec"])
    assert framework.conflicted(doc) == set()
    doc["findings"][-1]["subjects"] = ["X4"]
    hit = framework.conflicted(doc)
    assert "X4.security" in hit and "X4.method" in hit and not any(p.startswith("X3") for p in hit)
    doc["findings"][-1]["subjects"] = ["T1.default_path"]
    assert framework.conflicted(doc) == {"T1.default_path.%s" % k for k in
                                         ("events_of_default", "enforcement", "loss_waterfall", "recovery_history")}


def test_gap_subjects_do_not_conflict():
    doc = load_fixture()
    assert any(f["type"] == "gap" and f["subjects"] for f in doc["findings"])
    doc["findings"] = [f for f in doc["findings"] if f["type"] != "discrepancy"]
    assert framework.conflicted(doc) == set()


def test_flag_mapping():
    claim = {"value": 1, "status": "verified", "evidence": ["S4"], "subject": None, "note": ""}
    assert framework.flag(claim, False) == "CONFIRMED"
    assert framework.flag(dict(claim, status="self_reported"), False) == "PARTIALLY_VERIFIED"
    assert framework.flag(dict(claim, status="inferred"), False) == "PARTIALLY_VERIFIED"
    assert framework.flag(dict(claim, status="not_found", value=None), False) == "UNRESOLVED"
    assert framework.flag(claim, True) == "CONFLICTING"


def test_flags_cover_every_claim():
    doc = load_fixture()
    flags = framework.flags(doc)
    assert set(flags) == {parts for parts, _ in schema.iter_claims(doc)}
    assert flags[("interfaces", 3, "security")] == "CONFLICTING"
    assert flags[("interfaces", 3, "collateral")] == "PARTIALLY_VERIFIED"
    assert set(flags.values()) == set(schema.ENUMS["evidence_flag"])


# --------------------------------------------------------------------------- 3.2

def _table(doc):
    return {sid: [fl for _, _, fl in checks] for sid, checks in framework.completeness(doc)}


def test_completeness_on_fixture():
    rows = framework.completeness(load_fixture())
    assert [sid for sid, _ in rows] == ["T1", "T2"]
    assert [code for code, _, _ in rows[0][1]] == ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
    assert _table(load_fixture()) == {
        "T1": ["CONFIRMED", "PARTIALLY_VERIFIED", "PARTIALLY_VERIFIED", "CONFLICTING", "PARTIALLY_VERIFIED",
               "PARTIALLY_VERIFIED", "PARTIALLY_VERIFIED"],
        "T2": ["CONFIRMED", "UNRESOLVED", "PARTIALLY_VERIFIED", "PARTIALLY_VERIFIED", "UNRESOLVED",
               "PARTIALLY_VERIFIED", "PARTIALLY_VERIFIED"]}


def test_completeness_worst_flag_wins():
    doc = load_fixture()
    # T1 has two L2_L3 interfaces: X4 security is CONFLICTING, X5 security UNRESOLVED -> CONFLICTING.
    assert _table(doc)["T1"][3] == "CONFLICTING"
    doc["findings"] = [f for f in doc["findings"] if f["id"] != "D2"]
    assert _table(doc)["T1"][3] == "UNRESOLVED"
    doc["interfaces"][4]["security"] = copy.deepcopy(doc["interfaces"][3]["security"])
    assert _table(doc)["T1"][3] == "PARTIALLY_VERIFIED"


def test_completeness_missing_objects_unresolved():
    doc = load_fixture()
    doc["interfaces"] = []
    doc["holder_rights"] = []
    for e in doc["entities"]:
        e["functions"] = [fn for fn in e["functions"] if fn["role"] != "holder_counterparty"]
    assert _table(doc)["T1"][:4] == ["UNRESOLVED"] * 4 and _table(doc)["T1"][5] == "UNRESOLVED"


def test_completeness_counterparty_strategy_scope():
    doc = load_fixture()
    doc["entities"][0]["functions"][1]["strategy"] = "T2"
    assert _table(doc)["T1"][0] == "UNRESOLVED" and _table(doc)["T2"][0] == "CONFIRMED"


# --------------------------------------------------------------------------- 3.3

T1_LINES = [
    "P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E5 Acme Credit Fund LP (L2) -> [DI] -> "
    "E6 Acme Warehouse SPV Ltd (L2) -> [DL; secured] -> E7 Example Equipment Lessors Ltd (L3) -> [OTHER] -> "
    "E10 (L3-O)",
    "P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E5 Acme Credit Fund LP (L2) -> [DI] -> "
    "E6 Acme Warehouse SPV Ltd (L2) -> [AP; ?] -> E8 Example Receivables Originator (L3)",
]
T2_LINES = ["P2 holders -> [OTHER] -> E1 Acme Yield Issuer Ltd (L1/L2) -> [PT; unsecured] -> E9 (L3)"]


def _iface(doc, ident, kind, src, dst):
    x = copy.deepcopy(doc["interfaces"][2])  # X3, within_L2, legal class DI
    x.update({"id": ident, "kind": kind, "from": src, "to": dst})
    return x


def test_chain_lines_on_fixture():
    doc = load_fixture()
    assert framework.chain_line(doc, "T1") == T1_LINES
    assert framework.chain_line(doc, "T2") == T2_LINES


def test_chain_line_l1_l2_entity_jumps_to_l3():
    doc = load_fixture()
    assert framework.chain_line(doc, "T2") == T2_LINES
    doc["entities"][0]["functions"] = [fn for fn in doc["entities"][0]["functions"] if fn["layer"] != "L2"]
    assert framework.chain_line(doc, "T2") == [
        "P2 holders -> [OTHER] -> E1 Acme Yield Issuer Ltd (L1)",
        "E1 Acme Yield Issuer Ltd (L2) -> [PT; unsecured] -> E9 (L3)"]


def test_chain_line_branches_in_id_order():
    doc = load_fixture()
    # E6 has two continuations, X4 (to E7) and X5 (to E8): two lines sharing the prefix, X4 first.
    lines = framework.chain_line(doc, "T1")
    assert len(lines) == 2 and lines[0].endswith("E10 (L3-O)") and lines[1].endswith("(L3)")
    assert lines[0].split(" -> [DL")[0] == lines[1].split(" -> [AP")[0]


def test_chain_line_cycle_terminates():
    doc = load_fixture()
    doc["interfaces"].append(_iface(doc, "X9", "within_L2", "E6", "E5"))
    lines = framework.chain_line(doc, "T1")
    assert lines == T1_LINES  # X3 E5->E6 and X9 E6->E5: E5 is already on the path, so X9 is never followed


def test_chain_line_orphan_start():
    doc = load_fixture()
    doc["interfaces"][2]["from"] = "E2"  # X3 no longer leaves E5, so E6 is unreachable from holders
    assert framework.chain_line(doc, "T1") == [
        "P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E5 Acme Credit Fund LP (L2)",
        "E6 Acme Warehouse SPV Ltd (L2) -> [DL; secured] -> E7 Example Equipment Lessors Ltd (L3) -> [OTHER] -> "
        "E10 (L3-O)",
        "E6 Acme Warehouse SPV Ltd (L2) -> [AP; ?] -> E8 Example Receivables Originator (L3)",
    ]


def test_chain_line_within_never_starts():
    doc = load_fixture()
    doc["interfaces"] = [x for x in doc["interfaces"] if x["kind"].startswith("within_")]
    assert [x["id"] for x in doc["interfaces"]] == ["X3", "X8"]
    assert framework.chain_line(doc, "T1") == []


def test_chain_line_unknown_entity_and_empty():
    doc = load_fixture()
    doc["entities"][4]["functions"] = []
    assert framework.chain_line(doc, "T1") == T1_LINES  # labels show the position, not the entity's functions
    doc["interfaces"][1]["to"] = "E99"
    assert framework.chain_line(doc, "T1")[0] == \
        "P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E99 (?)"
    doc["interfaces"] = []
    assert framework.chain_line(doc, "T1") == []
