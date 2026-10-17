"""Test groups 1 and 3: the fixture is valid; reference integrity and structure."""

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
        doc["findings"][3]["type"] = "gap"
    assert "findings[3].id: prefix of C1 does not match type gap" in errors_for(m)


def test_non_dense_ids():
    doc = json.loads(json.dumps(load_fixture()).replace('"E4"', '"E5"'))
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
        doc["governing_law"]["confidence"] = 1
        doc["extra"] = True
    assert errors_for(m) == ['(root): unknown key "extra"', 'governing_law: unknown key "confidence"']


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


def test_every_product_needs_edge_and_yield():
    def m(doc):
        doc["yield"] = [y for y in doc["yield"] if y["product"] != "P2"]
        for e in doc["flows"]["edges"]:
            e["products"] = ["P1"]
    assert errors_for(m) == ["project.products[1]: P2 has no flow edge", "project.products[1]: P2 has no yield entry"]


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
