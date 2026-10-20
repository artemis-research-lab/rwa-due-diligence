"""Test groups 1 and 3: the fixture is valid; reference integrity and structure; v0.5.0 framework rules."""

import copy
import json

from test_support import build_run, claim, fixture_sources, load_fixture, run_cli
from lib import schema, validate


def errors_for(mutate):
    doc = copy.deepcopy(load_fixture())
    mutate(doc)
    return validate.validate_document(doc)


def test_fixture_is_valid_against_its_ledger():
    assert validate.validate_document(load_fixture(), fixture_sources()) == []


def test_validate_cli_exit_0_on_fixture_run_dir(tmp_path):
    build_run(tmp_path)
    code, out, err = run_cli(["validate", "--slug", "acme", "--root", str(tmp_path)])
    assert (code, out, err) == (0, "valid\n", "")


def test_dangling_edge_node():
    def m(doc):
        doc["flows"]["edges"][0]["to"] = "n42"
    assert errors_for(m) == ["flows.edges[0].to: unknown node n42"]


def test_dangling_product():
    def m(doc):
        doc["redemption"][1]["product"] = "P7"
    assert errors_for(m) == ["redemption[1].product: unknown product P7"]


def test_wrong_finding_prefix():
    def m(doc):
        doc["findings"][5]["type"] = "gap"
    assert "findings[5].id: prefix of C1 does not match type gap" in errors_for(m)


def test_non_dense_ids():
    doc = json.loads(json.dumps(load_fixture()).replace('"E14"', '"E15"'))
    assert validate.validate_document(doc) == ["entities: E ids must be dense from E1"]


def test_duplicate_id():
    def m(doc):
        doc["next_searches"][1]["id"] = "N1"
    assert "next_searches[1].id: duplicate id N1" in errors_for(m)


def test_unknown_key():
    def m(doc):
        doc["entities"][0]["website"] = "https://x.example"
    assert errors_for(m) == ['entities[0]: unknown key "website"']


def test_unknown_key_in_claim_and_root():
    def m(doc):
        doc["holder_rights"][0]["governing_law"]["confidence"] = 1
        doc["extra"] = True
    assert errors_for(m) == ['(root): unknown key "extra"', 'holder_rights[0].governing_law: unknown key "confidence"']


def test_removed_1_0_keys_are_unknown():
    def m(doc):
        doc["relationships"] = []
        doc["governing_law"] = None
    assert errors_for(m) == ['(root): unknown key "governing_law"', '(root): unknown key "relationships"']


def test_control_character():
    def m(doc):
        doc["findings"][0]["statement"] = "line one\nline two"
    assert errors_for(m) == ["findings[0].statement: control character not allowed"]


def test_control_character_inside_claim_value():
    def m(doc):
        doc["project"]["asset_class"]["value"] = ["ok", "tab\there"]
    assert errors_for(m) == ["project.asset_class.value[1]: control character not allowed"]


def test_string_over_limit():
    def m(doc):
        doc["flows"]["nodes"][0]["label"] = "x" * 41
    assert errors_for(m) == ["flows.nodes[0].label: longer than 40 characters"]


def test_missing_key_and_bad_enum():
    def m(doc):
        del doc["audits"][0]["scope"]
        doc["flows"]["edges"][0]["rail"] = "carrier_pigeon"
    assert errors_for(m) == ['audits[0]: missing key "scope"', "flows.edges[0].rail: not a valid rail"]


def test_history_order():
    def m(doc):
        doc["history"].reverse()
    assert errors_for(m) == ["history: must be sorted by date (nulls last)"]


def test_other_references():
    def m(doc):
        doc["audits"][0]["report_ref"] = "S19"
        doc["next_searches"][0]["resolves"] = ["G5"]
        doc["x_unmapped"][0]["evidence"] = ["S10"]
    assert errors_for(m) == ["audits[0].report_ref: unknown source S19",
                             "next_searches[0].resolves[0]: unknown finding G5",
                             "x_unmapped[0].evidence[0]: unknown source S10"]

    def resolves_u_and_r(doc):
        doc["next_searches"][0]["resolves"] = ["U1", "R1"]
    assert errors_for(resolves_u_and_r) == []

    def resolves_c(doc):
        doc["next_searches"][0]["resolves"] = ["C1"]
    assert errors_for(resolves_c) == ["next_searches[0].resolves[0]: must be id G<n>|D<n>|U<n>|R<n>"]


def test_errors_are_sorted_and_unique():
    def m(doc):
        doc["flows"]["edges"][0]["to"] = "n42"
        doc["flows"]["edges"][1]["to"] = "n42"
    errs = errors_for(m)
    assert errs == sorted(set(errs)) and len(errs) == 2


# --------------------------------------------------------------------------- C1: flow node ref accepts chain addresses

def _with_ref(ref):
    def m(doc):
        doc["flows"]["nodes"][0]["ref"] = ref
    return errors_for(m)


def test_node_ref_accepts_chain_addresses():
    assert _with_ref("7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV" + "1") == []      # base58 Solana, 44 chars
    assert _with_ref("pb1w6ul64t5fjcg65mmscec758dgyml6xmmw5fy2vyxxc9gvzrvkqls7zr4t") == []  # Provenance bech32
    assert _with_ref("0x00000000000000000000000000000000000000a1") == []          # EVM


def test_node_ref_rejects_malformed():
    assert _with_ref("0x00 a1") == ["flows.nodes[0].ref: must be E<n>|P<n>|chain address <alphanumeric, 1..64>"]
    assert _with_ref("a" * 65) == ["flows.nodes[0].ref: must be E<n>|P<n>|chain address <alphanumeric, 1..64>"]
    assert _with_ref("E0") == ["flows.nodes[0].ref: unknown entity/product E0"]


# --------------------------------------------------------------------------- v0.5.0 section 2

def test_t_x_q_ids_dense_and_unique():
    def m(doc):
        doc["interfaces"][6]["id"] = "X14"
        doc["issuer_requests"][1]["id"] = "Q1"
    errs = errors_for(m)
    assert "interfaces: X ids must be dense from X1" in errs
    assert "issuer_requests[1].id: duplicate id Q1" in errs
    doc = json.loads(json.dumps(load_fixture()).replace('"T3"', '"T4"'))
    assert validate.validate_document(doc) == ["strategies: T ids must be dense from T1"]


def test_strategy_and_function_references():
    def m(doc):
        doc["strategies"][1]["products"] = ["P2", "P5"]
        doc["entities"][0]["functions"][2]["strategy"] = "T7"
        doc["entities"][0]["functions"][2]["evidence"] = ["S30"]
    assert errors_for(m) == ["entities[0].functions[2].evidence[0]: unknown source S30",
                             "entities[0].functions[2].strategy: unknown strategy T7",
                             "strategies[1].products[1]: unknown product P5"]


def test_function_evidence_required():
    def m(doc):
        doc["entities"][0]["functions"][0]["evidence"] = []
    assert errors_for(m) == ["entities[0].functions[0].evidence: needs at least 1 item(s)"]


def test_interface_references():
    def m(doc):
        doc["interfaces"][1]["strategy"] = "T4"
        doc["interfaces"][1]["to"] = "E19"
        doc["interfaces"][2]["from"] = "E18"
        doc["holder_rights"][0]["product"] = "P3"
    errs = errors_for(m)
    for e in ("interfaces[1].strategy: unknown strategy T4", "interfaces[1].to: unknown entity E19",
              "interfaces[2].from: unknown entity/product E18", "holder_rights[0].product: unknown product P3"):
        assert e in errs


def test_interface_to_must_be_entity():
    def m(doc):
        doc["interfaces"][1]["to"] = "P1"
    assert errors_for(m) == ["interfaces[1].to: must be id E<n>"]


def test_product_from_only_for_holder_l1():
    def m(doc):
        doc["interfaces"][1]["from"] = "P1"
    assert errors_for(m) == ["interfaces[1].from: a product id is allowed only for kind holder_L1"]

    def m2(doc):
        doc["interfaces"][0]["from"] = "E4"
    assert errors_for(m2) == ["interfaces[0].from: kind holder_L1 requires a product id"]


def test_interface_from_and_to_must_differ():
    def m(doc):
        doc["interfaces"][2]["to"] = "E5"
    assert errors_for(m) == ["interfaces[2]: from and to must differ (E5)"]


def test_edge_strategy_and_interface_references():
    def m(doc):
        doc["flows"]["edges"][0]["strategies"] = ["T1", "T5"]
        doc["flows"]["edges"][1]["interface"] = "X19"
    assert errors_for(m) == ["flows.edges[0].strategies[1]: unknown strategy T5",
                             "flows.edges[1].interface: unknown interface X19"]


def test_edge_needs_strategy_and_view():
    def m(doc):
        doc["flows"]["edges"][0]["strategies"] = []
        doc["flows"]["edges"][1]["view"] = "loss"
    assert errors_for(m) == ["flows.edges[0].strategies: needs at least 1 item(s)",
                             "flows.edges[1].view: not a valid flow_view"]


def test_finding_subjects_leading_id_must_exist():
    def m(doc):
        doc["findings"][4]["subjects"] = ["X4.security", "X19.security", "T1.not_a_field", "E19", "Z2.coverage"]
    assert errors_for(m) == ["findings[4].subjects[1]: unknown id X19",
                             "findings[4].subjects[2]: T1.not_a_field does not resolve",
                             "findings[4].subjects[3]: unknown id E19", "findings[4].subjects[4]: unknown id Z2"]

    def digits(doc):
        doc["findings"][4]["subjects"] = ["T2.l3_business.performance", "P1.holder_rights.look_through"]
    assert errors_for(digits) == []

    def bad(doc):
        doc["findings"][4]["subjects"] = ["X4.Security"]
    assert errors_for(bad) == ["findings[4].subjects[0]: must be subject path (E|P|T|X|Z)<n>[.field[<i>]]{0,4}"]


def test_coverage_product_in_strategy_and_holder_rights():
    def m(doc):
        doc["strategies"][1]["products"] = ["P1"]
        doc["strategies"][2]["products"] = ["P1"]
        doc["holder_rights"].append(copy.deepcopy(doc["holder_rights"][0]))
        doc["holder_rights"] = [h for h in doc["holder_rights"] if h["product"] != "P2"]
    assert errors_for(m) == ["project.products[0]: P1 needs exactly one holder_rights entry (found 2)",
                             "project.products[1]: P2 is in no strategy",
                             "project.products[1]: P2 needs exactly one holder_rights entry (found 0)"]


def test_coverage_yield_and_settlement_edge():
    def m(doc):
        doc["yield"] = [y for y in doc["yield"] if y["product"] != "P2"]
        for e in doc["flows"]["edges"]:
            if "T2" in e["strategies"] and e["view"] == "settlement":
                e["view"] = "claim"
    assert errors_for(m) == ["project.products[1]: P2 has no yield entry",
                             "strategies[1]: T2 has no flow edge with view settlement"]


def test_strategies_need_one_item():
    def m(doc):
        doc["strategies"] = []
    assert "strategies: needs at least 1 item(s)" in errors_for(m)


def _set(doc, path, value):
    node = doc
    for part in path[:-1]:
        node = node[part]
    node[path[-1]]["value"] = value


def test_coded_claims_one_of_enum():
    cases = [(("strategies", 0, "business_type"), "credit", "business_type"),
             (("interfaces", 1, "route"), "pool", "route_code"),
             (("interfaces", 1, "legal_class"), ["FI"], "legal_class"),
             (("interfaces", 3, "security"), "SECURED", "security"),
             (("holder_rights", 0, "look_through"), "spv", "look_through")]
    for path, value, enum in cases:
        def m(doc):
            _set(doc, path, value)
        label = ".".join(str(p) if isinstance(p, str) else "[%d]" % p for p in path).replace(".[", "[")
        assert errors_for(m) == ["%s: value must be one of %s" % (label, enum)]

    def ok(doc):
        _set(doc, ("interfaces", 1, "route"), "WRAPPER")
        _set(doc, ("holder_rights", 1, "look_through"), "none")
    assert errors_for(ok) == []


def test_coded_claim_method_list():
    for value in ("DL", [], ["DL", "DL"], ["DL", "LOAN"], [1]):
        def m(doc):
            _set(doc, ("interfaces", 3, "method"), value)
        assert errors_for(m) == ["interfaces[3].method: value must be a non-empty list of method_code"], value

    def ok(doc):
        _set(doc, ("interfaces", 3, "method"), ["DL", "AP"])
    assert errors_for(ok) == []


def test_coded_claim_loss_waterfall():
    for value in ("Borrower equity", [], ["a", 2]):
        def m(doc):
            _set(doc, ("strategies", 0, "default_path", "loss_waterfall"), value)
        assert errors_for(m) == ["strategies[0].default_path.loss_waterfall: value must be a non-empty list of "
                                 "strings"], value


def test_null_coded_claims_pass():
    def m(doc):
        doc["interfaces"][3]["security"] = claim()
    assert errors_for(m) == []


def test_kind_constraints_route_and_method():
    def m(doc):
        doc["interfaces"][0]["route"] = copy.deepcopy(doc["interfaces"][1]["route"])
        doc["interfaces"][1]["method"] = claim(None, "not_found", ["S8"], note="Not applicable.")
    assert errors_for(m) == [
        "interfaces[0].route: must be not_found without evidence unless kind is L1_L2",
        "interfaces[1].method: must be not_found without evidence unless kind is L2_L3 or L3_L3O"]


def test_seeded_from_null_or_string():
    def m(doc):
        doc["run"]["seeded_from"] = "acme-20260901T000000Z"
    assert errors_for(m) == []

    def bad(doc):
        doc["run"]["seeded_from"] = 3
    assert errors_for(bad) == ["run.seeded_from: must be a string"]


def test_issuer_request_rules():
    def m(doc):
        doc["issuer_requests"][0]["answers"] = []
        doc["issuer_requests"][1]["answers"] = ["Z9"]
        doc["issuer_requests"][1]["priority"] = 4
    assert errors_for(m) == ["issuer_requests[0].answers: needs at least 1 item(s)",
                             "issuer_requests[1].answers[0]: not a valid question_code",
                             "issuer_requests[1].priority: out of range (integer 1..3)"]


# --------------------------------------------------------------------------- v0.6.0 section 2.2

NF = claim()


def _x(doc, xid):
    return next(x for x in doc["interfaces"] if x["id"] == xid)


def test_z_and_u_ids_dense_and_unique():
    def m(doc):
        doc["supports"][0]["id"] = "Z2"
        doc["findings"][6]["id"] = "U2"
    assert errors_for(m) == ["findings: U ids must be dense from U1", "findings[6].subjects[0]: unknown id Z1",
                             "supports: Z ids must be dense from Z1"]

    def dup(doc):
        doc["supports"].append(copy.deepcopy(doc["supports"][0]))
    assert errors_for(dup) == ["supports[1].id: duplicate id Z1"]


def test_u_prefix_follows_type():
    def m(doc):
        doc["findings"][6]["type"] = "gap"
    assert "findings[6].id: prefix of U1 does not match type gap" in errors_for(m)


def test_support_references():
    def m(doc):
        doc["supports"][0].update({"strategies": ["T1", "T9"], "provider": "E20", "beneficiary": "P5"})
    assert errors_for(m) == ["supports[0].beneficiary: unknown entity/product P5",
                             "supports[0].provider: unknown entity E20",
                             "supports[0].strategies[1]: unknown strategy T9"]

    def ok(doc):
        doc["supports"][0]["beneficiary"] = None
    assert errors_for(ok) == []

    def product(doc):
        doc["supports"][0]["beneficiary"] = "P1"
    assert errors_for(product) == []


def test_alternative_both_or_neither():
    def m(doc):
        _x(doc, "X12")["alternative"]["option"] = None
    errs = errors_for(m)
    assert "interfaces[11].alternative: group and option must both be set or both null" in errs
    assert "alternative group A1 needs at least two options" in errs

    def ok(doc):
        for xid in ("X11", "X12"):
            _x(doc, xid)["alternative"] = {"group": None, "option": None}
    assert errors_for(ok) == []


def test_alternative_needs_two_distinct_options():
    def m(doc):
        _x(doc, "X12")["alternative"]["option"] = "a"
    assert errors_for(m) == ["alternative group A1 needs at least two options"]


def test_alternative_group_spans_strategies():
    def m(doc):
        _x(doc, "X4")["alternative"] = {"group": "A1", "option": "c"}
    assert errors_for(m) == ["alternative group A1 spans strategies"]


def test_alternative_patterns():
    def m(doc):
        _x(doc, "X11")["alternative"] = {"group": "B1", "option": "A"}
    assert errors_for(m) == ["interfaces[10].alternative.group: must be A<n>",
                             "interfaces[10].alternative.option: must be letter a-z"]


def test_amount_value_is_a_number():
    for value in ("25m", True, -1, [1]):
        def m(doc):
            _x(doc, "X2")["amounts"][0]["value"]["value"] = value
        assert errors_for(m) == ["interfaces[1].amounts[0].value: value must be a number >= 0"], value

    def ok(doc):
        _x(doc, "X2")["amounts"][0]["value"]["value"] = 0.5
    assert errors_for(ok) == []


def test_kind_constraints_2_1():
    def m(doc):
        _x(doc, "X2")["title_transfer"] = copy.deepcopy(_x(doc, "X13")["title_transfer"])
        _x(doc, "X4")["servicing"] = dict(NF, evidence=["S8"], note="n/a")
        _x(doc, "X4")["residual_exposure"] = dict(NF, evidence=["S8"], note="n/a")
    assert errors_for(m) == [
        "interfaces[1].title_transfer: must be not_found without evidence unless kind is asset_sale",
        "interfaces[3].residual_exposure: must be not_found without evidence unless kind is asset_sale",
        "interfaces[3].servicing: must be not_found without evidence unless kind is asset_sale"]

    def ok(doc):
        _x(doc, "X8")["method"] = claim(["OTHER"], "self_reported", ["S8"])
    assert errors_for(ok) == []


def test_discrepancy_needs_scope_note():
    def m(doc):
        doc["findings"][3]["scope_note"] = ""
        doc["findings"][4]["scope_note"] = "  "
    assert errors_for(m) == ["findings[3].scope_note: required for a discrepancy",
                             "findings[4].scope_note: required for a discrepancy"]

    def others(doc):
        doc["findings"][6]["scope_note"] = ""
        doc["findings"][7]["scope_note"] = ""
    assert errors_for(others) == ["findings[6].scope_note: required for a scope_unresolved",
                                  "findings[7].scope_note: required for a unreconciled_transaction"]

    def gap(doc):
        doc["findings"][0]["scope_note"] = ""
    assert errors_for(gap) == []


def test_function_layer_null_only_for_listed_roles():
    def m(doc):
        doc["entities"][4]["functions"][0]["layer"] = None
    assert errors_for(m) == ["entities[4].functions[0].layer: required for role lender_of_record"]
    for role in ("issuer", "loan_purchaser", "protection_provider", "reserve_assets", "auditor", "other"):
        def ok(doc):
            doc["entities"][4]["functions"][0].update({"layer": None, "role": role})
        assert errors_for(ok) == [], role


def test_sleeve_needs_no_settlement_edge_but_core_and_defi_do():
    doc = load_fixture()
    assert not any("T3" in e["strategies"] for e in doc["flows"]["edges"])

    def defi(doc):
        doc["strategies"][2]["component"] = "DEFI_LENDING"
    assert errors_for(defi) == ["strategies[2]: T3 has no flow edge with view settlement"]

    def core(doc):
        doc["strategies"][2]["component"] = "CORE_CREDIT"
    assert errors_for(core) == ["strategies[2]: T3 has no flow edge with view settlement"]


# --------------------------------------------------------------------------- v0.7.0 section 2.2

def _f(doc, fid):
    return next(f for f in doc["findings"] if f["id"] == fid)


def test_fixture_findings_by_index():
    assert [f["id"] for f in load_fixture()["findings"]] == ["G1", "G2", "G3", "D1", "D2", "C1", "U1", "R1"]


def test_r_ids_dense_and_prefix():
    def m(doc):
        _f(doc, "R1")["id"] = "R2"
    assert errors_for(m) == ["findings: R ids must be dense from R1"]

    def wrong(doc):
        _f(doc, "R1")["type"] = "scope_unresolved"
    assert "findings[7].id: prefix of R1 does not match type scope_unresolved" in errors_for(wrong)


def test_coded_ratio_and_deployment():
    for value in (1.5, -0.1, True, "half"):
        def m(doc):
            _x(doc, "X2")["supply_concentration"]["ratio"]["value"] = value
        assert errors_for(m) == ["interfaces[1].supply_concentration.ratio: value must be a number 0..1"], value
    for value in (0, 1, 0.25):
        def ok(doc):
            _x(doc, "X2")["supply_concentration"]["ratio"]["value"] = value
        assert errors_for(ok) == [], value

    def deployment(doc):
        doc["strategies"][1]["deployment"]["value"] = "DEPLOYED"
    assert errors_for(deployment) == ["strategies[1].deployment: value must be one of deployment"]


def _amount(doc, xid, j=0):
    return _x(doc, xid)["amounts"][j]


def test_amount_entry_rules():
    def not_found(doc):
        _amount(doc, "X9")["value"] = claim()
    assert errors_for(not_found) == [
        "interfaces[8].amounts[0].value: an amount entry needs a value; remove the entry instead"]

    def blank(doc):
        _amount(doc, "X9").update({"unit": " ", "scope": ""})
    assert errors_for(blank) == ["interfaces[8].amounts[0].scope: required", "interfaces[8].amounts[0].unit: required"]

    def position(doc):
        _amount(doc, "X2", 1)["valuation_basis"] = None
    assert errors_for(position) == ["interfaces[1].amounts[1].valuation_basis: required for POSITION_VALUE"]

    def other(doc):
        _amount(doc, "X9").update({"basis": "OTHER", "scope": "too short scope"})
    assert errors_for(other) == [
        "interfaces[8].amounts[0].scope: OTHER needs an explicit definition (>= 20 characters)"]

    def other_ok(doc):
        _amount(doc, "X9").update({"basis": "OTHER", "scope": "Stablecoin held on behalf of P2 holders"})
    assert errors_for(other_ok) == []

    def block(doc):
        _amount(doc, "X2")["chain"] = None
    assert errors_for(block) == ["interfaces[1].amounts[0].chain: required when block is set"]

    def bad_time(doc):
        _amount(doc, "X9")["as_of"] = "2026-02-30"
    assert errors_for(bad_time) == ["interfaces[8].amounts[0].as_of: not a real date_or_timestamp"]

    def bad_unit(doc):
        _amount(doc, "X9")["unit"] = "U" * 21
    assert errors_for(bad_unit) == ["interfaces[8].amounts[0].unit: longer than 20 characters"]


def test_amount_kind_constraints():
    def holder(doc):
        _x(doc, "X1")["amounts"] = copy.deepcopy(_x(doc, "X9")["amounts"])
    assert errors_for(holder) == ["interfaces[0].amounts: not allowed on holder_L1"]

    def reserve(doc):
        _amount(doc, "X9")["basis"] = "RESERVE_LOOKTHROUGH"
    assert errors_for(reserve) == ["interfaces[8].amounts[0].basis: RESERVE_LOOKTHROUGH not allowed on sleeve_holding"]

    def proceeds(doc):
        _amount(doc, "X2")["basis"] = "SALE_PROCEEDS"
    assert errors_for(proceeds) == ["interfaces[1].amounts[0].basis: SALE_PROCEEDS not allowed on L1_L2"]

    def commitment(doc):
        _amount(doc, "X9")["basis"] = "UNDRAWN_COMMITMENT"
    assert errors_for(commitment) == ["interfaces[8].amounts[0].basis: UNDRAWN_COMMITMENT not allowed on "
                                      "sleeve_holding"]

    def ok(doc):
        _amount(doc, "X2")["basis"] = "FACILITY_COMMITMENT"
        _x(doc, "X3")["amounts"] = copy.deepcopy(_x(doc, "X4")["amounts"])
    assert errors_for(ok) == []


def test_supply_concentration_rules():
    def elsewhere(doc):
        _x(doc, "X4")["supply_concentration"] = copy.deepcopy(_x(doc, "X2")["supply_concentration"])
    assert errors_for(elsewhere) == [
        "interfaces[3].supply_concentration: must be not_found without evidence unless kind is L1_L2"]

    def text_only(doc):
        _x(doc, "X4")["supply_concentration"]["numerator"] = "x"
    assert errors_for(text_only) == [
        "interfaces[3].supply_concentration: must be not_found without evidence unless kind is L1_L2"]

    def incomplete(doc):
        _x(doc, "X2")["supply_concentration"].update({"denominator": "", "as_of": None})
    assert errors_for(incomplete) == [
        "interfaces[1].supply_concentration: numerator, denominator and as_of are required with a ratio"]


def test_asset_sale_fields_kind_constraint():
    for field in ("loan_identity", "seller_of_record", "buyer_of_record", "repayment_source"):
        def m(doc):
            _x(doc, "X4")[field] = copy.deepcopy(_x(doc, "X13")[field])
        assert errors_for(m) == ["interfaces[3].%s: must be not_found without evidence unless kind is asset_sale"
                                 % field], field


def test_deployment_rules():
    def sleeve(doc):
        doc["strategies"][2]["deployment"] = copy.deepcopy(doc["strategies"][1]["deployment"])
    assert errors_for(sleeve) == [
        "strategies[2].deployment: must be not_found without evidence unless component is CORE_CREDIT or "
        "DEFI_LENDING"]

    def unverified(doc):
        doc["strategies"][1]["deployment"]["value"] = "DEPLOYED_VERIFIED"
    assert errors_for(unverified) == ["strategies[1].deployment: DEPLOYED_VERIFIED requires status verified"]

    def defi(doc):
        doc["strategies"][1]["component"] = "DEFI_LENDING"
    assert errors_for(defi) == []


def test_scope_match_by_type():
    cases = [("G1", "matched", "gap"), ("C1", "unchecked", "structural_change"), ("D1", "not_matched", "discrepancy"),
             ("D1", "unchecked", "discrepancy"), ("U1", "matched", "scope_unresolved"),
             ("R1", "not_applicable", "unreconciled_transaction")]
    for fid, value, kind in cases:
        def m(doc):
            _f(doc, fid)["scope_match"] = value
        index = [f["id"] for f in load_fixture()["findings"]].index(fid)
        assert errors_for(m) == ["findings[%d].scope_match: %s not allowed for %s" % (index, value, kind)], fid

    def placeholder(doc):
        _f(doc, "D1").update({"scope_note": schema.MIGRATED_NOTE_21 + " -- old", "scope_match": "unchecked"})
        _f(doc, "U1")["scope_match"] = "unchecked"
        _f(doc, "R1")["scope_match"] = "not_matched"
    assert errors_for(placeholder) == []


def test_assertion_rules():
    def one(doc):
        _f(doc, "D1")["assertions"] = _f(doc, "D1")["assertions"][:1]
        _f(doc, "U1")["assertions"] = []
        _f(doc, "R1")["assertions"] = []
    assert errors_for(one) == ["findings[3].assertions: at least two statements required for discrepancy",
                               "findings[6].assertions: at least two statements required for scope_unresolved",
                               "findings[7].assertions: at least two statements required for "
                               "unreconciled_transaction"]

    def placeholder(doc):
        _f(doc, "U1").update({"assertions": [], "scope_note": schema.MIGRATED_SCOPE_NOTE})
    assert errors_for(placeholder) == []

    def outside(doc):
        _f(doc, "D1")["assertions"][1]["source"] = "S4"
    assert errors_for(outside) == ["findings[3].assertions[1].source: not in evidence"]

    def gap(doc):
        _f(doc, "G2")["assertions"] = copy.deepcopy(_f(doc, "D1")["assertions"])
        _f(doc, "C1")["assertions"] = copy.deepcopy(_f(doc, "D1")["assertions"])
    errs = errors_for(gap)
    assert "findings[1].assertions: must be empty for gap" in errs
    assert "findings[5].assertions: must be empty for structural_change" in errs


def test_discrepancy_subjects_are_claims():
    def none(doc):
        _f(doc, "D1")["subjects"] = []
    assert errors_for(none) == ["findings[3].subjects: at least one claim required for a discrepancy"]

    def placeholder(doc):
        _f(doc, "D1").update({"subjects": [], "scope_note": schema.MIGRATED_NOTE_21, "scope_match": "unchecked",
                              "assertions": []})
    assert errors_for(placeholder) == []

    def objects(doc):
        _f(doc, "D1")["subjects"] = ["X6", "X2.amounts", "X2.amounts[0]", "X2.amounts[0].value"]
    assert errors_for(objects) == ["findings[3].subjects[0]: X6 is not a claim",
                                   "findings[3].subjects[1]: X2.amounts is not a claim",
                                   "findings[3].subjects[2]: X2.amounts[0] is not a claim"]

    def other_types(doc):
        _f(doc, "G1")["subjects"] = ["X2.amounts[0]", "X2.supply_concentration.ratio", "P1.holder_rights"]
        _f(doc, "U1")["subjects"] = ["X2.amounts"]
        _f(doc, "R1")["subjects"] = ["X13.amounts[3]"]
    assert errors_for(other_types) == ["findings[6].subjects[0]: X2.amounts is not a claim or object",
                                       "findings[7].subjects[0]: X13.amounts[3] does not resolve"]


def test_resolution_rules():
    def structural(doc):
        _f(doc, "C1")["resolution"]["status"] = "open"
    assert errors_for(structural) == ["findings[5].resolution.status: open not allowed for structural_change"]

    def gap(doc):
        _f(doc, "G2")["resolution"]["status"] = "not_applicable"
    assert errors_for(gap) == ["findings[1].resolution.status: not_applicable not allowed for gap"]

    def no_note(doc):
        _f(doc, "D2")["resolution"]["note"] = " "
    assert errors_for(no_note) == ["findings[4].resolution.note: required when resolved"]

    def resolved_gap(doc):
        _f(doc, "G2")["resolution"] = {"status": "resolved", "note": "Yield disclosed in the October report."}
    assert errors_for(resolved_gap) == []


def test_k_checks_impact_priority_carried_from():
    def dup(doc):
        _f(doc, "G1")["k_checks"] = ["K1", "K1"]
        _f(doc, "G1")["impact"] = ["ownership", "ownership"]
    assert errors_for(dup) == ["findings[0].impact: duplicate value", "findings[0].k_checks: duplicate value"]

    def bad(doc):
        _f(doc, "G1").update({"k_checks": ["K8"], "impact": ["control"], "priority": 4, "carried_from": "N1"})
    assert errors_for(bad) == ["findings[0].carried_from: must be finding id G|D|C|U|R<n>",
                               "findings[0].impact[0]: not a valid impact",
                               "findings[0].k_checks[0]: not a valid k_check",
                               "findings[0].priority: out of range (integer 1..3)"]

    def carried_twice(doc):
        _f(doc, "G3")["carried_from"] = "G3"
    assert errors_for(carried_twice) == ["findings[7].carried_from: G3 already carried by G3"]
