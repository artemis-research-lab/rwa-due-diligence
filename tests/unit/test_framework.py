"""v0.5.0/v0.6.0/v0.7.0 framework view: claim ids, conflicts, flags, completeness, chain lines, allocation and
totals, the six questions, the section 1 selection and resolve."""

import copy

import pytest

from test_support import claim, load_fixture
from lib import framework, schema


def _discrepancy(doc, subjects, scope_match="matched", status="open"):
    doc["findings"].append({
        "id": "D3", "type": "discrepancy", "topic": "credit", "blocking": False, "material": False,
        "statement": "x", "scope_note": "same", "scope_match": scope_match, "evidence": ["S5", "S8"],
        "subjects": subjects,
        "assertions": [{"source": "S5", "statement": "a", "as_of": None}, {"source": "S8", "statement": "b",
                                                                          "as_of": None}],
        "resolution": {"status": status, "note": "settled" if status == "resolved" else ""},
        "k_checks": [], "impact": [], "priority": 2, "carried_from": None})


def _without_open_conflicts(doc):
    doc["findings"] = [f for f in doc["findings"] if f["id"] != "D1"]
    return doc


# --------------------------------------------------------------------------- 3.1

def test_claim_id_examples():
    doc = load_fixture()
    cases = {
        ("interfaces", 1, "amounts", 0, "value"): "X2.amounts[0].value",
        ("interfaces", 1, "amounts", 2, "value"): "X2.amounts[2].value",
        ("interfaces", 1, "supply_concentration", "ratio"): "X2.supply_concentration.ratio",
        ("interfaces", 12, "loan_identity"): "X13.loan_identity",
        ("strategies", 0, "default_path", "loss_waterfall"): "T1.default_path.loss_waterfall",
        ("strategies", 1, "deployment"): "T2.deployment",
        ("holder_rights", 0, "look_through"): "P1.holder_rights.look_through",
        ("holder_rights", 1, "claim_against"): "P2.holder_rights.claim_against",
        ("supports", 0, "coverage"): "Z1.coverage",
        ("entities", 1, "licenses", 0, "regulator"): "E2.licenses[0].regulator",
        ("project", "products", 1, "symbol"): "P2.symbol",
        ("project", "name"): "project.name",
        ("yield", 0, "gross_yield"): "yield[0].gross_yield",
        ("yield", 0, "underlying", 0, "description"): "yield[0].underlying[0].description",
        ("onchain", "contracts", 0, "proxy"): "onchain.contracts[0].proxy",
        ("flows", "edges", 0, "claim"): "flows.edges[0].claim",
    }
    for parts, expected in cases.items():
        assert framework.claim_id(parts, doc) == expected, parts


def test_claim_ids_unique_and_flags_by_id_sorted():
    doc = load_fixture()
    ids = [framework.claim_id(parts, doc) for parts, _ in schema.iter_claims(doc)]
    assert len(ids) == len(set(ids))
    by_id = framework.flags_by_id(doc)
    assert list(by_id) == sorted(ids)
    assert by_id["X6.terms"] == "CONFLICTING" and by_id["X2.amounts[0].value"] == "CONFIRMED"
    assert by_id["X2.amounts[2].value"] == "SELF_REPORTED" and by_id["project.name"] == "SELF_REPORTED"


def test_subject_path_examples():
    doc = load_fixture()
    assert framework.subject_path(("interfaces", 3, "security"), doc) == "X4.security"
    assert framework.subject_path(("strategies", 0, "default_path", "loss_waterfall"), doc) == \
        "T1.default_path.loss_waterfall"
    assert framework.subject_path(("entities", 1, "legal_name"), doc) == "E2.legal_name"
    assert framework.subject_path(("entities", 1, "licenses", 0, "regulator"), doc) == "E2.licenses[0].regulator"
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
    assert framework.conflicted(load_fixture()) == {"X6.terms"}


def test_only_open_matched_discrepancies_flag():
    doc = _without_open_conflicts(load_fixture())
    assert framework.conflicted(doc) == set()  # D2 on X4.security is resolved
    _discrepancy(doc, ["X4.security"], scope_match="unchecked")
    assert framework.conflicted(doc) == set()
    doc["findings"][-1]["scope_match"] = "matched"
    assert framework.conflicted(doc) == {"X4.security"}
    doc["findings"][-1]["resolution"] = {"status": "resolved", "note": "settled"}
    assert framework.conflicted(doc) == set()


def test_unreconciled_transaction_never_flags():
    doc = _without_open_conflicts(load_fixture())
    r1 = doc["findings"][-1]
    assert r1["id"] == "R1" and r1["subjects"] == ["X13"]
    r1["subjects"] = ["X13", "X13.title_transfer"]
    assert framework.conflicted(doc) == set()
    assert framework.flags(doc)[("interfaces", 12, "title_transfer")] == "SELF_REPORTED"


def test_conflict_status_and_rows():
    doc = load_fixture()
    status = {f["id"]: framework.conflict_status(f) for f in doc["findings"]}
    assert status == {"G1": None, "G2": None, "G3": None, "D1": "CONFLICTING", "D2": "RESOLVED", "C1": None,
                      "U1": "SCOPE_UNRESOLVED", "R1": "UNRECONCILED_TRANSACTION"}
    assert framework.conflicts(doc) == [
        ("D1", "CONFLICTING", "matched", "open", ["X6.terms"], ["S7", "S1"]),
        ("D2", "RESOLVED", "matched", "resolved", ["X4.security"], ["S8", "S5"]),
        ("R1", "UNRECONCILED_TRANSACTION", "matched", "open", ["X13"], ["S8", "S5"]),
        ("U1", "SCOPE_UNRESOLVED", "not_matched", "open", ["Z1.coverage"], ["S8", "S5"])]
    unchecked = dict(doc["findings"][3], scope_match="unchecked")
    assert framework.conflict_status(unchecked) is None


def test_conflicted_prefix_at_field_boundary():
    doc = load_fixture()
    doc["findings"] = [f for f in doc["findings"] if f["type"] != "discrepancy"]
    _discrepancy(doc, ["X3.sec"])
    assert framework.conflicted(doc) == set()
    doc["findings"][-1]["subjects"] = ["X2.amounts"]
    assert framework.conflicted(doc) == {"X2.amounts[%d].value" % j for j in range(3)}
    doc["findings"][-1]["subjects"] = ["X2.amounts[1].value"]
    assert framework.conflicted(doc) == {"X2.amounts[1].value"}
    doc["findings"][-1]["subjects"] = ["X3.sec"]
    assert framework.conflicted(doc) == set()
    doc["findings"][-1]["subjects"] = ["X4"]
    hit = framework.conflicted(doc)
    assert "X4.security" in hit and "X4.method" in hit and "X4.amounts[1].value" in hit
    assert not any(p.startswith("X3") for p in hit)
    doc["findings"][-1]["subjects"] = ["T1.default_path"]
    assert framework.conflicted(doc) == {"T1.default_path.%s" % k for k in
                                         ("events_of_default", "enforcement", "loss_waterfall", "recovery_history")}


def test_scope_unresolved_subjects_do_not_conflict():
    doc = load_fixture()
    assert [f["subjects"] for f in doc["findings"] if f["type"] == "scope_unresolved"] == [["Z1.coverage"]]
    assert "Z1.coverage" not in framework.conflicted(doc)
    assert framework.flags(doc)[("supports", 0, "coverage")] == "SELF_REPORTED"
    doc["findings"][6]["scope_match"] = "unchecked"
    assert "Z1.coverage" not in framework.conflicted(doc)
    _discrepancy(doc, ["Z1.coverage"])
    assert "Z1.coverage" in framework.conflicted(doc)
    assert framework.flags(doc)[("supports", 0, "coverage")] == "CONFLICTING"


def test_gap_subjects_do_not_conflict():
    doc = load_fixture()
    assert any(f["type"] == "gap" and f["subjects"] for f in doc["findings"])
    doc["findings"] = [f for f in doc["findings"] if f["type"] != "discrepancy"]
    assert framework.conflicted(doc) == set()


def test_flag_mapping():
    claim = {"value": 1, "status": "verified", "evidence": ["S4"], "subject": None, "note": "", "origin": None,
             "assurance": None}
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
    assert flags[("interfaces", 5, "terms")] == "CONFLICTING"
    assert flags[("interfaces", 3, "security")] == "SELF_REPORTED"  # D2 is resolved
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
        "T1": ["CONFIRMED", "SELF_REPORTED", "SELF_REPORTED", "UNRESOLVED", "SELF_REPORTED",
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
    # T1 has two L2_L3 interfaces: X4 security is SELF_REPORTED, X5 security UNRESOLVED -> UNRESOLVED.
    assert _table(doc)["T1"][3] == "UNRESOLVED"
    _discrepancy(doc, ["X4.security"])
    assert _table(doc)["T1"][3] == "CONFLICTING"
    doc["findings"].pop()
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
    T1_HEAD + " -> [sale; true sale; loan INFERRED] -> E13 Example Loan Buyer Fund (transferee)",
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
        "E6 Acme Warehouse SPV Ltd (L2) -> [sale; true sale; loan INFERRED] -> E13 Example Loan Buyer Fund "
        "(transferee)",
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
        "E6 Acme Warehouse SPV Ltd (L2) -> [sale; true sale; loan INFERRED] -> E13 Example Loan Buyer Fund "
        "(transferee)"]


def test_chain_line_title_transfer_unknown():
    doc = load_fixture()
    doc["interfaces"][12]["title_transfer"] = claim()
    doc["interfaces"][12]["loan_identity"] = claim()
    assert framework.chain_line(doc, "T1")[2].endswith(
        " -> [sale; ?; loan UNRESOLVED] -> E13 Example Loan Buyer Fund (transferee)")


# --------------------------------------------------------------------------- 3.4

ROWS = [
    ("T1", "CORE_CREDIT", "X2", 0, "L1_L2", 25000000, "USDC", "CURRENT_BALANCE", "2026-09-30T12:00:00Z",
     "USDC supplied by E1 to the E5 credit pool, read at the block", True, "counted"),
    ("T1", "CORE_CREDIT", "X2", 1, "L1_L2", 25150000, "USD", "POSITION_VALUE", "2026-09-30",
     "E1 units in Acme Credit Fund LP", False, "other measure of X2[0]"),
    ("T1", "CORE_CREDIT", "X2", 2, "L1_L2", 18000000, "USD", "CUMULATIVE_FUNDED", "2026-06-30",
     "AUP loan sample: 12 loans funded 2026-01-01 to 2026-06-30 (S9); management figure, not tested", False,
     "basis CUMULATIVE_FUNDED not counted"),
    ("T1", "CORE_CREDIT", "X13", 0, "asset_sale", 3000000, "USD", "SALE_PROCEEDS", "2026-08-15",
     "Proceeds of the X13 loan sale to E13", False, "not a funding edge"),
    ("T3", "LIQUIDITY_SLEEVE", "X9", 0, "sleeve_holding", 5000000, "USDC", "CURRENT_BALANCE", "2026-10-01",
     "Stablecoin held by E1 in the treasury sleeve", True, "counted"),
    ("T3", "LIQUIDITY_SLEEVE", "X10", 0, "reserve_lookthrough", 5000000, "USD", "RESERVE_LOOKTHROUGH", "2026-09-30",
     "Reserve assets of E11 backing the sleeve stablecoin", False, "not a funding edge"),
]


def _total(basis, unit, as_of, value, valuation_basis=None, **extra):
    return dict({"basis": basis, "unit": unit, "as_of": as_of, "valuation_basis": valuation_basis, "sum": value,
                 "label": "%s %s %s @%s" % (value, unit, basis, as_of)}, **extra)


T1_TOTALS = [_total("CURRENT_BALANCE", "USDC", "2026-09-30", 25000000)]
T3_TOTALS = [_total("CURRENT_BALANCE", "USDC", "2026-10-01", 5000000)]


def test_allocation_rows():
    rows = framework.allocation(load_fixture())
    assert rows == ROWS
    assert [r.valuation_basis for r in rows] == [None, "Fund NAV per unit reported by E5", None, None, None, None]
    assert rows[1].as_object() == dict(zip(framework.ROW_FIELDS, ROWS[1]),
                                       valuation_basis="Fund NAV per unit reported by E5",
                                       observed_at="2026-10-01T08:40:00Z", time_basis="source")
    assert framework.total_key(rows[0]) == ("CURRENT_BALANCE", "USDC", "2026-09-30", "")
    assert framework.total_key(rows[1]) == ("POSITION_VALUE", "USD", "2026-09-30", "Fund NAV per unit reported by E5")


def test_allocation_totals():
    assert framework.allocation_totals(load_fixture()) == {
        "strategies": {"T1": T1_TOTALS, "T3": T3_TOTALS},
        "components": {"CORE_CREDIT": T1_TOTALS, "LIQUIDITY_SLEEVE": T3_TOTALS},
        "products": {"P1": [dict(t, shared=False) for t in T1_TOTALS],
                     "P2": [dict(t, shared=False) for t in T3_TOTALS]}}


def _reasons(doc):
    return [(r[2], r[3], r[10], r[11]) for r in framework.allocation(doc)]


def test_allocation_every_reason():
    doc = load_fixture()
    x2 = doc["interfaces"][1]
    x2["alternative"] = {"group": "A2", "option": "a"}
    assert _reasons(doc)[0] == ("X2", 0, False, "alternative A2a")
    x2["alternative"] = {"group": None, "option": None}
    assert _reasons(doc)[2] == ("X2", 2, False, "basis CUMULATIVE_FUNDED not counted")
    assert _reasons(doc)[3] == ("X13", 0, False, "not a funding edge")
    x2["amounts"][0]["as_of"] = None
    assert _reasons(doc)[0] == ("X2", 0, False, "data time not established")
    x2["amounts"][0]["scope"] = schema.MIGRATED_AMOUNT_SCOPE
    x2["amounts"][0]["as_of"] = "2026-09-30"
    assert _reasons(doc)[0] == ("X2", 0, False, "migrated scope")
    x2["amounts"] = []
    assert framework.allocation(doc)[0] == ("T1", "CORE_CREDIT", "X2", None, "L1_L2", None, None, None, None, None,
                                            False, "no amount")
    doc["interfaces"][9]["amounts"][0]["basis"] = "CURRENT_BALANCE"  # X10 reserve look-through
    assert [r for r in _reasons(doc) if r[0] == "X10"] == [("X10", 0, False, "not a funding edge")]
    assert framework.allocation_totals(doc)["strategies"] == {"T3": T3_TOTALS}


def test_time_basis_and_observed_at_per_row():
    doc = load_fixture()
    rows = framework.allocation(doc)
    assert [(r[2], r[3], r.time_basis, r.observed_at) for r in rows] == [
        ("X2", 0, "block", "2026-10-01T08:15:00Z"), ("X2", 1, "source", "2026-10-01T08:40:00Z"),
        ("X2", 2, "source", "2026-10-01T09:00:00Z"), ("X13", 0, "source", "2026-10-01T08:40:00Z"),
        ("X9", 0, "source", "2026-10-01T08:30:00Z"), ("X10", 0, "source", "2026-10-01T08:30:00Z")]
    amount = doc["interfaces"][1]["amounts"][1]
    amount["value"]["evidence"] = ["S6", "S2", "S8", "S4"]  # S6 has no retrieval time
    assert framework.observed_at(doc, amount) == "2026-10-01T08:40:00Z"
    amount["value"]["evidence"] = ["S6"]
    assert framework.observed_at(doc, amount) is None
    amount["as_of"] = None
    assert framework.time_basis(amount) == "unresolved"
    assert framework.allocation(doc)[1].as_object()["time_basis"] == "unresolved"
    doc["interfaces"][1]["amounts"] = []
    row = framework.allocation(doc)[0]
    assert (row.time_basis, row.observed_at) == (None, None)


def test_retrieval_source_string_and_instant():
    doc = load_fixture()
    amount = doc["interfaces"][1]["amounts"][1]  # cites S8, retrieved 2026-10-01T08:40:00Z
    assert framework.retrieval_source(doc, amount) is None
    amount["as_of"] = "2026-10-01T08:40:00Z"
    assert framework.retrieval_source(doc, amount) == "S8"
    amount["as_of"] = "2026-10-01"  # a date is never the same instant as a timestamp
    assert framework.retrieval_source(doc, amount) is None
    amount["as_of"] = "2026-10-01T08:40:00Z"
    amount["block"], amount["chain"] = 1, "ethereum"  # a block read keeps its block time
    assert framework.retrieval_source(doc, amount) is None


def test_resolve_target():
    doc = load_fixture()
    assert framework.resolve_target(doc, "@G3.type") == ("R1", "G3")
    assert framework.resolve_target(doc, "@D1") == ("D1", "D1")
    assert framework.resolve_target(doc, "G3.statement") == ("G3", None)
    assert framework.resolve_target(doc, "P1.holder_rights.look_through") == ("P1", None)
    assert framework.resolve_target(doc, "X13.amounts[5]") == ("X13", None)
    for path in ("@G9", "X99.terms", "x2"):
        with pytest.raises(KeyError):
            framework.resolve_target(doc, path)


def test_totals_never_merge_keys(monkeypatch):
    monkeypatch.setattr(framework, "_one_measure", lambda x, reasons: reasons)  # several measures of one edge
    doc = load_fixture()
    x9 = doc["interfaces"][8]
    x9["amounts"].append(dict(copy.deepcopy(x9["amounts"][0]), as_of="2026-09-01"))
    assert framework.allocation_totals(doc)["strategies"]["T3"] == [
        _total("CURRENT_BALANCE", "USDC", "2026-09-01", 5000000), T3_TOTALS[0]]
    x9["amounts"].append(dict(copy.deepcopy(x9["amounts"][0]), as_of="2026-10-01T18:00:00Z"))
    assert framework.allocation_totals(doc)["strategies"]["T3"][1] == _total("CURRENT_BALANCE", "USDC",
                                                                             "2026-10-01", 10000000)
    x9["amounts"].append(dict(copy.deepcopy(x9["amounts"][0]), unit="USDT"))
    assert len(framework.allocation_totals(doc)["strategies"]["T3"]) == 3
    t1 = framework.allocation_totals(load_fixture())["strategies"]["T1"]
    assert [t["basis"] for t in t1] == ["CURRENT_BALANCE", "POSITION_VALUE"]  # never summed together
    assert t1[1] == _total("POSITION_VALUE", "USD", "2026-09-30", 25150000, "Fund NAV per unit reported by E5")


def test_totals_by_product_marks_shared_strategies():
    doc = load_fixture()
    doc["strategies"][2]["products"] = ["P1", "P2"]
    totals = framework.allocation_totals(doc)
    assert totals["products"]["P1"] == [dict(T1_TOTALS[0], shared=True), dict(T3_TOTALS[0], shared=True)]
    assert totals["products"]["P2"] == [dict(T3_TOTALS[0], shared=True)]
    assert totals["components"] == {"CORE_CREDIT": T1_TOTALS, "LIQUIDITY_SLEEVE": T3_TOTALS}


def _measures(*amounts):
    """Fixture whose X2 carries only the given (basis, unit) amounts, all with an observation time."""
    doc = load_fixture()
    x2 = doc["interfaces"][1]
    template = x2["amounts"][0]
    x2["amounts"] = [dict(copy.deepcopy(template), basis=basis, unit=unit,
                          valuation_basis="Pool share price" if basis == "POSITION_VALUE" else None)
                     for basis, unit in amounts]
    return doc


def test_one_counted_measure_per_edge():
    doc = _measures(("CURRENT_BALANCE", "YLDS"), ("CURRENT_BALANCE", "HEYLDS"), ("POSITION_VALUE", "USD"))
    assert [r[2:4] + r[10:] for r in framework.allocation(doc) if r[2] == "X2"] == [
        ("X2", 0, True, "counted"), ("X2", 1, False, "other measure of X2[0]"),
        ("X2", 2, False, "other measure of X2[0]")]
    assert [t["unit"] for t in framework.allocation_totals(doc)["strategies"]["T1"]] == ["YLDS"]


def test_first_countable_entry_is_the_measure():
    doc = _measures(("CUMULATIVE_FUNDED", "USD"), ("CURRENT_BALANCE", "USDC"))
    assert [r[2:4] + r[10:] for r in framework.allocation(doc) if r[2] == "X2"] == [
        ("X2", 0, False, "basis CUMULATIVE_FUNDED not counted"), ("X2", 1, True, "counted")]
    totals = framework.allocation_totals(doc)["strategies"]["T1"]
    assert [(t["basis"], t["unit"]) for t in totals] == [("CURRENT_BALANCE", "USDC")]


def test_alternative_l2_l3_amount_not_in_allocation():
    doc = load_fixture()
    x11 = doc["interfaces"][10]
    assert x11["alternative"]["group"] == "A1" and x11["amounts"][0]["basis"] == "CURRENT_BALANCE"
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
    ("Is deployment verified?", "DEPLOYED_VERIFIED [CONFIRMED]"),
]


def test_six_questions_t1():
    assert framework.five_questions(load_fixture(), "T1") == T1_QUESTIONS


def test_six_questions_deployment_row():
    doc = load_fixture()
    assert dict(framework.five_questions(doc, "T2"))["Is deployment verified?"] == \
        "DISCLOSED_UNVERIFIED [SELF_REPORTED]"
    assert dict(framework.five_questions(doc, "T3"))["Is deployment verified?"] == "UNRESOLVED"


def test_five_questions_t2_alternatives_and_unresolved():
    answers = dict(framework.five_questions(load_fixture(), "T2"))
    assert answers["Who deploys credit?"] == (
        "E1 Acme Yield Issuer Ltd (L1/L2) [SELF_REPORTED]; E1 Acme Yield Issuer Ltd (L1/L2) [SELF_REPORTED; alt A1a]; "
        "E1 Acme Yield Issuer Ltd (L1/L2) [SELF_REPORTED; alt A1b]")
    assert answers["Who must repay?"] == answers["Who receives financing?"]
    assert answers["Who can enforce the claim?"] == "UNRESOLVED"


def test_five_questions_conflicting_and_empty():
    doc = load_fixture()
    _discrepancy(doc, ["X4"])
    answers = dict(framework.five_questions(doc, "T1"))
    assert answers["Who receives financing?"].startswith("E7 Example Equipment Lessors Ltd (L3) [CONFLICTING]; ")
    doc["interfaces"] = []
    doc["holder_rights"] = []
    doc["strategies"][0]["deployment"] = claim()
    assert [a for _, a in framework.five_questions(doc, "T1")] == ["UNRESOLVED"] * 6


# --------------------------------------------------------------------------- v0.7.0 3.5 section 1 selection

def test_critical_on_fixture():
    doc = load_fixture()
    assert framework.critical(doc) == ["R1", "G1", "G3", "U1"]
    assert framework.critical_counts(doc) == (4, 8, 2)  # G2 and D1 stay open outside section 1


def _f(doc, fid):
    return next(f for f in doc["findings"] if f["id"] == fid)


def test_critical_groups_and_order():
    doc = load_fixture()
    _f(doc, "D1").update({"material": True, "priority": 1})
    _f(doc, "G1")["priority"] = 2
    assert framework.critical(doc) == ["R1", "D1", "G1", "G3", "U1"]  # priority, then type R, D, U, G, C
    _f(doc, "U1")["k_checks"] = ["K4"]
    _f(doc, "G3")["priority"] = 3
    assert framework.critical(doc) == ["R1", "D1", "G1", "U1", "G3"]
    _f(doc, "U1").update({"k_checks": [], "impact": ["liquidity"]})
    assert "U1" not in framework.critical(doc)  # liquidity is not a section 1 impact
    _f(doc, "G2").update({"blocking": True, "impact": ["redemption"]})
    assert framework.critical(doc)[-1] == "G2"
    assert framework.critical_counts(doc) == (5, 8, 1)


def test_critical_has_no_cap():
    doc = load_fixture()
    for f in doc["findings"]:
        f["material"] = True
    assert len(framework.critical(doc)) == 8


# --------------------------------------------------------------------------- v0.7.0 3.6 resolve

def test_resolve_kinds():
    doc = load_fixture()
    assert framework.resolve(doc, "X2.amounts[0].value") == ("claim", doc["interfaces"][1]["amounts"][0]["value"])
    assert framework.resolve(doc, "X2.amounts[0]")[0] == "object"
    assert framework.resolve(doc, "X2.amounts")[0] == "list"
    assert framework.resolve(doc, "X2.amounts[0].unit") == ("scalar", "USDC")
    assert framework.resolve(doc, "X2.supply_concentration.ratio")[1]["value"] == 0.5
    assert framework.resolve(doc, "P1.holder_rights.look_through") == ("claim", doc["holder_rights"][0]["look_through"])
    assert framework.resolve(doc, "P2.holder_rights") == ("object", doc["holder_rights"][1])
    assert framework.resolve(doc, "P2.symbol")[0] == "claim"
    assert framework.resolve(doc, "E2.licenses[0].regulator")[0] == "claim"
    assert framework.resolve(doc, "T1.deployment")[1]["value"] == "DEPLOYED_VERIFIED"
    assert framework.resolve(doc, "Z1") == ("object", doc["supports"][0])
    assert framework.resolve(doc, "G3.k_checks") == ("list", ["K4"])


def test_resolve_carried_from():
    doc = load_fixture()
    assert framework.resolve(doc, "@G3")[1]["id"] == "R1"
    assert framework.resolve(doc, "@G3.type") == ("scalar", "unreconciled_transaction")
    assert framework.resolve(doc, "G3.type") == ("scalar", "gap")
    assert framework.resolve(doc, "@G1")[1]["id"] == "G1"
    assert framework.resolve(doc, "@R1")[1]["id"] == "R1"  # nothing carries from R1


@pytest.mark.parametrize("path", ["X99", "X2.nope", "X2.amounts[9]", "X2.amounts[0].value.value", "x2", "X2.",
                                  "N1", "X2.amounts.0", "P9.holder_rights", "@G9", "S1"])
def test_resolve_missing(path):
    with pytest.raises(KeyError):
        framework.resolve(load_fixture(), path)
