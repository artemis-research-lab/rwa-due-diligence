"""v0.5.0/v0.6.0 framework view: subject paths, conflicts, flags, completeness, chain lines, allocation and
the five questions."""

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
    assert framework.subject_path(("supports", 0, "coverage"), doc) == "Z1.coverage"
    assert framework.subject_path(("interfaces", 12, "title_transfer"), doc) == "X13.title_transfer"


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


def test_scope_unresolved_subjects_do_not_conflict():
    doc = load_fixture()
    assert [f["subjects"] for f in doc["findings"] if f["type"] == "scope_unresolved"] == [["Z1.coverage"]]
    assert "Z1.coverage" not in framework.conflicted(doc)
    assert framework.flags(doc)[("supports", 0, "coverage")] == "SELF_REPORTED"
    _discrepancy(doc, ["Z1.coverage"])
    assert "Z1.coverage" in framework.conflicted(doc)
    assert framework.flags(doc)[("supports", 0, "coverage")] == "CONFLICTING"


def test_gap_subjects_do_not_conflict():
    doc = load_fixture()
    assert any(f["type"] == "gap" and f["subjects"] for f in doc["findings"])
    doc["findings"] = [f for f in doc["findings"] if f["type"] != "discrepancy"]
    assert framework.conflicted(doc) == set()


def test_flag_mapping():
    claim = {"value": 1, "status": "verified", "evidence": ["S4"], "subject": None, "note": ""}
    assert framework.flag(claim, False) == "CONFIRMED"
    assert framework.flag(dict(claim, status="self_reported"), False) == "SELF_REPORTED"
    assert framework.flag(dict(claim, status="third_party_reported"), False) == "THIRD_PARTY_REPORTED"
    assert framework.flag(dict(claim, status="inferred"), False) == "INFERRED"
    assert framework.flag(dict(claim, status="not_found", value=None), False) == "UNRESOLVED"
    assert framework.flag(claim, True) == "CONFLICTING"


def test_flags_cover_every_claim():
    doc = load_fixture()
    flags = framework.flags(doc)
    assert set(flags) == {parts for parts, _ in schema.iter_claims(doc)}
    assert flags[("interfaces", 3, "security")] == "CONFLICTING"
    assert flags[("interfaces", 3, "collateral")] == "SELF_REPORTED"
    assert flags[("strategies", 0, "l3_business", "concentration")] == "THIRD_PARTY_REPORTED"
    assert set(flags.values()) == set(schema.ENUMS["evidence_flag"])


def test_severity_order():
    assert framework.SEVERITY == ("CONFLICTING", "UNRESOLVED", "INFERRED", "THIRD_PARTY_REPORTED", "SELF_REPORTED",
                                  "CONFIRMED")
    assert set(framework.SEVERITY) == set(schema.ENUMS["evidence_flag"])
    assert framework.worst(["CONFIRMED", "SELF_REPORTED", "THIRD_PARTY_REPORTED"]) == "THIRD_PARTY_REPORTED"
    assert framework.worst(["THIRD_PARTY_REPORTED", "INFERRED"]) == "INFERRED"
    assert framework.worst([]) == "UNRESOLVED"


# --------------------------------------------------------------------------- 3.2

def _table(doc):
    return {sid: [fl for _, _, fl in checks] for sid, checks in framework.completeness(doc)}


def test_completeness_on_fixture():
    rows = framework.completeness(load_fixture())
    assert [sid for sid, _ in rows] == ["T1", "T2"]
    assert [code for code, _, _ in rows[0][1]] == ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
    assert _table(load_fixture()) == {
        "T1": ["CONFIRMED", "SELF_REPORTED", "SELF_REPORTED", "CONFLICTING", "SELF_REPORTED",
               "SELF_REPORTED", "SELF_REPORTED"],
        "T2": ["CONFIRMED", "UNRESOLVED", "SELF_REPORTED", "SELF_REPORTED", "UNRESOLVED",
               "INFERRED", "SELF_REPORTED"]}


def test_completeness_only_for_core_credit():
    doc = load_fixture()
    assert [t["component"] for t in doc["strategies"]] == ["CORE_CREDIT", "CORE_CREDIT", "LIQUIDITY_SLEEVE"]
    doc["strategies"][1]["component"] = "DEFI_LENDING"
    assert [sid for sid, _ in framework.completeness(doc)] == ["T1"]
    doc["strategies"][2]["component"] = "CORE_CREDIT"
    assert [sid for sid, _ in framework.completeness(doc)] == ["T1", "T3"]


def test_completeness_worst_flag_wins():
    doc = load_fixture()
    # T1 has two L2_L3 interfaces: X4 security is CONFLICTING, X5 security UNRESOLVED -> CONFLICTING.
    assert _table(doc)["T1"][3] == "CONFLICTING"
    doc["findings"] = [f for f in doc["findings"] if f["id"] != "D2"]
    assert _table(doc)["T1"][3] == "UNRESOLVED"
    doc["interfaces"][4]["security"] = copy.deepcopy(doc["interfaces"][3]["security"])
    assert _table(doc)["T1"][3] == "SELF_REPORTED"


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

T1_HEAD = ("P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E5 Acme Credit Fund LP (L2) -> "
           "[DI] -> E6 Acme Warehouse SPV Ltd (L2)")
T1_LINES = [
    T1_HEAD + " -> [DL; secured] -> E7 Example Equipment Lessors Ltd (L3) -> [OTHER] -> E10 (L3-O)",
    T1_HEAD + " -> [AP; ?] -> E8 Example Receivables Originator (L3)",
    T1_HEAD + " -> [sale; true sale] -> E13 Example Loan Buyer Fund (transferee)",
]
T2_HEAD = "P2 holders -> [OTHER] -> E1 Acme Yield Issuer Ltd (L1/L2)"
T2_LINES = [
    T2_HEAD + " -> [PT; unsecured] -> E9 (L3)",
    T2_HEAD + " -> [REPO; secured; alt A1a] -> E9 (L3)",
    T2_HEAD + " -> [PT; unsecured; alt A1b] -> E9 (L3)",
]
T3_LINES = ["E1 Acme Yield Issuer Ltd (L1) -> [OTHER] -> E11 Example Stablecoin Issuer Ltd (issuer) -> "
            "[look-through] -> E12 (reserve)"]


def _iface(doc, ident, kind, src, dst):
    x = copy.deepcopy(doc["interfaces"][2])  # X3, within_L2, legal class DI
    x.update({"id": ident, "kind": kind, "from": src, "to": dst})
    return x


def test_chain_lines_on_fixture():
    doc = load_fixture()
    assert framework.chain_line(doc, "T1") == T1_LINES
    assert framework.chain_line(doc, "T2") == T2_LINES
    assert framework.chain_line(doc, "T3") == T3_LINES


def test_chain_line_l1_l2_entity_jumps_to_l3():
    doc = load_fixture()
    assert framework.chain_line(doc, "T2") == T2_LINES
    doc["entities"][0]["functions"] = [fn for fn in doc["entities"][0]["functions"] if fn["layer"] != "L2"]
    assert framework.chain_line(doc, "T2") == [
        "P2 holders -> [OTHER] -> E1 Acme Yield Issuer Ltd (L1)",
        "E1 Acme Yield Issuer Ltd (L2) -> [PT; unsecured] -> E9 (L3)",
        "E1 Acme Yield Issuer Ltd (L2) -> [REPO; secured; alt A1a] -> E9 (L3)",
        "E1 Acme Yield Issuer Ltd (L2) -> [PT; unsecured; alt A1b] -> E9 (L3)"]


def test_chain_line_branches_in_id_order():
    doc = load_fixture()
    # E6 has three continuations, X4 (to E7), X5 (to E8) and the asset sale X13: lines share the prefix.
    lines = framework.chain_line(doc, "T1")
    assert len(lines) == 3 and lines[0].endswith("E10 (L3-O)") and lines[1].endswith("(L3)")
    assert lines[2].endswith("(transferee)")
    assert lines[0].split(" -> [DL")[0] == lines[1].split(" -> [AP")[0] == lines[2].split(" -> [sale")[0] == T1_HEAD


def test_chain_line_cycle_terminates():
    doc = load_fixture()
    doc["interfaces"].append(_iface(doc, "X14", "within_L2", "E6", "E5"))
    lines = framework.chain_line(doc, "T1")
    assert lines == T1_LINES  # X3 E5->E6 and X14 E6->E5: E5 is already on the path, so X9 is never followed


def test_chain_line_orphan_start():
    doc = load_fixture()
    doc["interfaces"][2]["from"] = "E2"  # X3 no longer leaves E5, so E6 is unreachable from holders
    assert framework.chain_line(doc, "T1") == [
        "P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E5 Acme Credit Fund LP (L2)",
        "E6 Acme Warehouse SPV Ltd (L2) -> [DL; secured] -> E7 Example Equipment Lessors Ltd (L3) -> [OTHER] -> "
        "E10 (L3-O)",
        "E6 Acme Warehouse SPV Ltd (L2) -> [AP; ?] -> E8 Example Receivables Originator (L3)",
        "E6 Acme Warehouse SPV Ltd (L2) -> [sale; true sale] -> E13 Example Loan Buyer Fund (transferee)",
    ]


def test_chain_line_within_never_starts():
    doc = load_fixture()
    doc["interfaces"] = [x for x in doc["interfaces"]
                         if x["kind"].startswith("within_") or x["kind"] in ("L3_L3O", "reserve_lookthrough")]
    assert [x["id"] for x in doc["interfaces"]] == ["X3", "X8", "X10"]
    assert framework.chain_line(doc, "T1") == [] and framework.chain_line(doc, "T3") == []


def test_chain_line_unknown_entity_and_empty():
    doc = load_fixture()
    doc["entities"][4]["functions"] = []
    assert framework.chain_line(doc, "T1") == T1_LINES  # labels show the position, not the entity's functions
    doc["interfaces"][1]["to"] = "E99"
    assert framework.chain_line(doc, "T1")[0] == \
        "P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E99 (?)"
    doc["interfaces"] = []
    assert framework.chain_line(doc, "T1") == []


def test_chain_line_sleeve_start_and_asset_sale_start():
    doc = load_fixture()
    doc["interfaces"] = [x for x in doc["interfaces"] if x["id"] in ("X9", "X10", "X13")]
    assert framework.chain_line(doc, "T3") == T3_LINES
    assert framework.chain_line(doc, "T1") == [
        "E6 Acme Warehouse SPV Ltd (L2) -> [sale; true sale] -> E13 Example Loan Buyer Fund (transferee)"]


def test_chain_line_title_transfer_unknown():
    doc = load_fixture()
    doc["interfaces"][12]["title_transfer"] = {"value": None, "status": "not_found", "evidence": [],
                                               "subject": None, "note": ""}
    assert framework.chain_line(doc, "T1")[2].endswith(" -> [sale; ?] -> E13 Example Loan Buyer Fund (transferee)")


# --------------------------------------------------------------------------- 3.4

def test_allocation_rows():
    assert framework.allocation(load_fixture()) == [
        ("T1", "CORE_CREDIT", "X2", "L1_L2", 25000000, None, "GROSS_FUNDED", True, "counted"),
        ("T1", "CORE_CREDIT", "X13", "asset_sale", 3000000, "USD", "SALE_PROCEEDS", False, "basis SALE_PROCEEDS"),
        ("T3", "LIQUIDITY_SLEEVE", "X9", "sleeve_holding", 5000000, "USD", "GROSS_FUNDED", True, "counted"),
        ("T3", "LIQUIDITY_SLEEVE", "X10", "reserve_lookthrough", 5000000, "USD", "LOOKTHROUGH", False,
         "basis LOOKTHROUGH"),
    ]


def test_allocation_totals():
    assert framework.allocation_totals(load_fixture()) == {
        "strategies": {"T1": {"n/d": 25000000}, "T3": {"USD": 5000000}},
        "components": {"CORE_CREDIT": {"n/d": 25000000}, "LIQUIDITY_SLEEVE": {"USD": 5000000}}}


def test_allocation_alternative_and_non_gross_not_counted():
    doc = load_fixture()
    x2 = doc["interfaces"][1]
    x2["alternative"] = {"group": "A2", "option": "a"}
    assert framework.allocation(doc)[0][7:] == (False, "alternative A2a")
    x2["alternative"] = {"group": None, "option": None}
    x2["amount_basis"] = "COMMITMENT"
    assert framework.allocation(doc)[0][7:] == (False, "basis COMMITMENT")
    x2["amount_basis"] = "GROSS_FUNDED"
    x2["amount"] = {"value": None, "status": "not_found", "evidence": [], "subject": None, "note": ""}
    assert framework.allocation(doc)[0][7:] == (False, "no amount")
    doc["interfaces"][9]["amount_basis"] = "GROSS_FUNDED"  # X10 reserve look-through
    assert framework.allocation(doc)[3][7:] == (False, "not a funding edge")
    assert framework.allocation_totals(doc) == {"strategies": {"T3": {"USD": 5000000}},
                                                "components": {"LIQUIDITY_SLEEVE": {"USD": 5000000}}}


def test_allocation_totals_group_by_currency():
    doc = load_fixture()
    doc["interfaces"][1]["currency"] = {"value": "USD", "status": "self_reported", "evidence": ["S8"],
                                        "subject": None, "note": ""}
    doc["interfaces"][8]["amount"]["value"] = 2.5
    totals = framework.allocation_totals(doc)
    assert totals["strategies"] == {"T1": {"USD": 25000000}, "T3": {"USD": 2.5}}
    doc["strategies"][2]["component"] = "CORE_CREDIT"
    assert framework.allocation_totals(doc)["components"] == {"CORE_CREDIT": {"USD": 25000002.5}}


def test_alternative_l2_l3_amount_not_in_allocation():
    doc = load_fixture()
    assert doc["interfaces"][10]["amount"]["value"] == 2000000 and doc["interfaces"][10]["amount_basis"] == \
        "GROSS_FUNDED"
    assert "X11" not in [row[2] for row in framework.allocation(doc)]


# --------------------------------------------------------------------------- 3.5

T1_QUESTIONS = [
    ("Who holds investor capital?", "E1 Acme Yield Issuer Ltd (L1) [SELF_REPORTED]"),
    ("Who deploys credit?", "E5 Acme Credit Fund LP (L2) [SELF_REPORTED]"),
    ("Who receives financing?",
     "E7 Example Equipment Lessors Ltd (L3) [SELF_REPORTED]; E8 Example Receivables Originator (L3) [SELF_REPORTED]"),
    ("Who must repay?",
     "E7 Example Equipment Lessors Ltd (L3) [SELF_REPORTED]; E8 Example Receivables Originator (L3) [SELF_REPORTED]; "
     "cash flows from: E10 (L3-O) [SELF_REPORTED]"),
    ("Who can enforce the claim?", "E1 [SELF_REPORTED]; Security agent E3 enforces on default [SELF_REPORTED]"),
]


def test_five_questions_t1():
    assert framework.five_questions(load_fixture(), "T1") == T1_QUESTIONS


def test_five_questions_t2_alternatives_and_unresolved():
    answers = dict(framework.five_questions(load_fixture(), "T2"))
    assert answers["Who deploys credit?"] == (
        "E1 Acme Yield Issuer Ltd (L1/L2) [SELF_REPORTED]; E1 Acme Yield Issuer Ltd (L1/L2) [SELF_REPORTED; alt A1a]; "
        "E1 Acme Yield Issuer Ltd (L1/L2) [SELF_REPORTED; alt A1b]")
    assert answers["Who must repay?"] == answers["Who receives financing?"]
    assert answers["Who can enforce the claim?"] == "UNRESOLVED"


def test_five_questions_conflicting_and_empty():
    doc = load_fixture()
    doc["findings"].append({"id": "D3", "type": "discrepancy", "topic": "credit", "blocking": False,
                            "material": False, "statement": "x", "scope_note": "same", "evidence": [],
                            "subjects": ["X4"]})
    answers = dict(framework.five_questions(doc, "T1"))
    assert answers["Who receives financing?"].startswith("E7 Example Equipment Lessors Ltd (L3) [CONFLICTING]; ")
    doc["interfaces"] = []
    doc["holder_rights"] = []
    assert [a for _, a in framework.five_questions(doc, "T1")] == ["UNRESOLVED"] * 5
