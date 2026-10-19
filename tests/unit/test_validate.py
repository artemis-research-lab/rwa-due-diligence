"""Test groups 1 and 3: the fixture is valid; reference integrity and structure; v0.5.0 framework rules."""

import copy
import json

from test_support import build_run, fixture_sources, load_fixture, run_cli
from lib import validate


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
    doc = json.loads(json.dumps(load_fixture()).replace('"E9"', '"E10"'))
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
        doc["audits"][0]["report_ref"] = "S9"
        doc["next_searches"][0]["resolves"] = ["G5"]
        doc["x_unmapped"][0]["evidence"] = ["S10"]
    assert errors_for(m) == ["audits[0].report_ref: unknown source S9",
                             "next_searches[0].resolves[0]: unknown finding G5",
                             "x_unmapped[0].evidence[0]: unknown source S10"]


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
        doc["interfaces"][6]["id"] = "X9"
        doc["issuer_requests"][1]["id"] = "Q1"
    errs = errors_for(m)
    assert "interfaces: X ids must be dense from X1" in errs
    assert "issuer_requests[1].id: duplicate id Q1" in errs
    doc = json.loads(json.dumps(load_fixture()).replace('"T2"', '"T3"'))
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
        doc["interfaces"][1]["to"] = "E12"
        doc["interfaces"][2]["from"] = "E11"
        doc["holder_rights"][0]["product"] = "P3"
    errs = errors_for(m)
    for e in ("interfaces[1].strategy: unknown strategy T4", "interfaces[1].to: unknown entity E12",
              "interfaces[2].from: unknown entity/product E11", "holder_rights[0].product: unknown product P3"):
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


def test_edge_strategy_and_interface_references():
    def m(doc):
        doc["flows"]["edges"][0]["strategies"] = ["T1", "T5"]
        doc["flows"]["edges"][1]["interface"] = "X8"
    assert errors_for(m) == ["flows.edges[0].strategies[1]: unknown strategy T5",
                             "flows.edges[1].interface: unknown interface X8"]


def test_edge_needs_strategy_and_view():
    def m(doc):
        doc["flows"]["edges"][0]["strategies"] = []
        doc["flows"]["edges"][1]["view"] = "loss"
    assert errors_for(m) == ["flows.edges[0].strategies: needs at least 1 item(s)",
                             "flows.edges[1].view: not a valid flow_view"]


def test_finding_subjects_leading_id_must_exist():
    def m(doc):
        doc["findings"][4]["subjects"] = ["X4.security", "X9.security", "T1.not_a_field", "E10"]
    assert errors_for(m) == ["findings[4].subjects[1]: unknown id X9", "findings[4].subjects[3]: unknown id E10"]

    def bad(doc):
        doc["findings"][4]["subjects"] = ["X4.Security"]
    assert errors_for(bad) == ["findings[4].subjects[0]: must be subject path (E|P|T|X)<n>[.field]{0,3}"]


def test_coverage_product_in_strategy_and_holder_rights():
    def m(doc):
        doc["strategies"][1]["products"] = ["P1"]
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
        doc["interfaces"][3]["security"] = {"value": None, "status": "not_found", "evidence": [], "subject": None,
                                            "note": ""}
    assert errors_for(m) == []


def test_kind_constraints_route_and_method():
    def m(doc):
        doc["interfaces"][0]["route"] = copy.deepcopy(doc["interfaces"][1]["route"])
        doc["interfaces"][1]["method"] = {"value": None, "status": "not_found", "evidence": ["S8"], "subject": None,
                                          "note": "Not applicable."}
    assert errors_for(m) == [
        "interfaces[0].route: must be not_found without evidence unless kind is L1_L2",
        "interfaces[1].method: must be not_found without evidence unless kind is L2_L3"]


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
