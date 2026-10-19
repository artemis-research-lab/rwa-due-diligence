import re

from test_support import ROOT, run_cli
from lib import schema, validate


def test_schema_doc_matches_committed_reference():
    # test 11
    committed = (ROOT / "references" / "schema.md").read_bytes().decode("utf-8")
    assert schema.schema_doc() == committed
    code, out, _ = run_cli(["schema-doc"])
    assert code == 0 and out == committed


def test_schema_doc_is_deterministic_and_ascii():
    text = schema.schema_doc()
    assert text == schema.schema_doc()
    assert text.isascii() and text.endswith("\n") and not text.endswith("\n\n")


def test_skeleton_is_structurally_valid_once_run_is_filled():
    doc = schema.skeleton(schema.DOCUMENT)
    doc["run"].update({"run_id": "x", "slug": "acme", "root_url": "https://a.example/",
                       "status": "draft", "started_at": "2026-01-01T00:00:00Z",
                       "skill_version": "0.1.0"})
    product = schema.skeleton(schema.PRODUCT)
    product["id"] = "P1"
    doc["project"]["products"] = [product]
    strategy = schema.skeleton(schema.STRATEGY)
    strategy.update({"id": "T1", "products": ["P1"], "component": "CORE_CREDIT"})
    doc["strategies"] = [strategy]
    assert validate.structural_errors(doc) == []
    assert doc["run"]["seeded_from"] is None and doc["schema_version"] == "rwa-dd/2.1"
    assert doc["supports"] == []
    interface = schema.skeleton(schema.INTERFACE)
    assert interface["alternative"] == {"group": None, "option": None} and interface["amount_basis"] is None
    support = schema.skeleton(schema.SUPPORT)
    support.update({"id": "Z1", "type": "YIELD_SUPPORT", "strategies": ["T1"], "provider": "E1"})
    assert validate.structural_errors(support, schema.SUPPORT) == []


def test_version_constants():
    assert (schema.SCHEMA_VERSION, schema.SKILL_VERSION) == ("rwa-dd/2.1", "0.6.0")
    assert schema.MIGRATED_SCOPE_NOTE == "unchecked (migrated from rwa-dd/2.0)"


def test_subject_pattern_field_names():
    pattern = re.compile(schema.SUBJECT_PATTERN)
    for ok in ("T1.l3_business.performance", "P1.holder_rights.look_through", "X3.security", "E10", "Z1.coverage"):
        assert pattern.match(ok), ok
    for bad in ("T1.3x", "T1.Field", "X1.a.b.c.d", "U1.coverage"):
        assert not pattern.match(bad), bad


def test_enums_contain_framework_values():
    e = schema.ENUMS
    for role in ("vault", "token_issuer", "protocol_operator", "holder_counterparty", "credit_manager",
                 "lender_of_record", "security_agent", "financing_recipient", "receivables_seller",
                 "asset_holding_spv", "guarantor", "issuer", "other", "contractual_obligor", "cash_flow_source",
                 "offtaker_customer", "loan_purchaser", "protection_provider", "reserve_assets"):
        assert role in e["role"]
    assert "ultimate_obligor" not in e["role"]
    assert e["layer"] == ("L1", "L2", "L3", "L3-O")
    assert e["interface_kind"] == ("holder_L1", "L1_L2", "L2_L3", "within_L1", "within_L2", "within_L3", "L3_L3O",
                                   "sleeve_holding", "reserve_lookthrough", "asset_sale")
    assert e["route_code"] == ("POOL", "FUND", "DIRECT", "WRAPPER")
    assert e["method_code"] == ("DL", "DI", "AP", "PI", "REPO", "PT", "OTHER")
    assert e["legal_class"] == ("DL", "DI", "AP", "PI", "FI", "EI", "PROTOCOL_ENTITLEMENT", "OTHER")
    assert e["component"] == ("CORE_CREDIT", "LIQUIDITY_SLEEVE", "DEFI_LENDING")
    assert e["amount_basis"] == ("GROSS_FUNDED", "COMMITMENT", "LOOKTHROUGH", "RESERVE", "SALE_PROCEEDS")
    assert e["entity_class"] == ("legal_person", "contract_or_pool", "program", "obligor_group", "unknown")
    assert e["support_type"] == ("CREDIT_ENHANCEMENT", "YIELD_SUPPORT")
    assert e["claim_status"] == ("verified", "self_reported", "third_party_reported", "inferred", "not_found")
    assert e["finding_type"] == ("gap", "discrepancy", "structural_change", "scope_unresolved")
    assert schema.FINDING_PREFIX["scope_unresolved"] == "U"
    assert e["security"] == ("secured", "unsecured", "partially_secured")
    assert e["look_through"] == ("none", "via_security_trust", "via_spv", "direct_claim", "unresolved")
    assert e["business_type"] == ("private_credit", "trade_finance_pt", "mixed", "other")
    assert e["flow_view"] == ("settlement", "claim", "repayment")
    assert e["evidence_flag"] == ("CONFIRMED", "SELF_REPORTED", "THIRD_PARTY_REPORTED", "INFERRED", "UNRESOLVED",
                                  "CONFLICTING")
    assert {"credit", "holder_rights", "business"} <= set(e["topic"])
    assert len(e["question_code"]) == 29 and e["question_code"][:2] == ("A1", "A2") and e["question_code"][-1] == "F3"
    assert "relationship_type" not in e


def test_document_key_order():
    assert schema.DOCUMENT.keys() == [
        "schema_version", "run", "project", "strategies", "sources", "entities", "interfaces", "holder_rights",
        "supports", "yield", "redemption", "eligibility", "audits", "size", "flows", "onchain", "history",
        "findings", "open_questions", "next_searches", "issuer_requests", "narrative", "x_unmapped"]
    assert schema.LEGAL_SECTIONS == ("entities", "interfaces", "holder_rights", "supports", "eligibility")


def test_2_1_document_additions():
    fields = dict(schema.DOCUMENT.fields)
    assert schema.STRATEGY.keys()[:4] == ["id", "products", "name", "component"]
    assert fields["entities"].item.keys()[:2] == ["id", "entity_class"]
    functions = dict(fields["entities"].item.fields)["functions"].item
    assert dict(functions.fields)["layer"].nullable
    keys = schema.INTERFACE.keys()
    assert keys[keys.index("recourse") + 1:] == ["alternative", "amount", "amount_basis", "supply_concentration",
                                                 "title_transfer", "servicing", "residual_exposure", "as_of"]
    assert schema.SUPPORT.keys() == ["id", "type", "strategies", "provider", "beneficiary", "covered_exposure",
                                     "trigger", "coverage", "exclusions", "priority", "enforceability",
                                     "governing_law", "holder_recourse"]
    finding = fields["findings"].item
    assert finding.keys() == ["id", "type", "topic", "blocking", "material", "statement", "scope_note", "evidence",
                              "subjects"]
    assert schema.CODED_CLAIMS[("interfaces", "amount")] == (None, "number")
    node_layer = dict(dict(fields["flows"].fields)["nodes"].item.fields)["layer"]
    assert re.match(node_layer.regex, "L3-O") and not re.match(node_layer.regex, "L4")


def test_schema_doc_documents_2_1():
    text = schema.schema_doc()
    assert text.startswith("# Schema rwa-dd/2.1\n")
    for needle in ("third_party_reported", "THIRD_PARTY_REPORTED", "scope_unresolved=U", "Counting rule",
                   "`P<n>.holder_rights.<field>`", "`Z1.coverage`", schema.MIGRATED_SCOPE_NOTE,
                   "Severity (worst first): CONFLICTING, UNRESOLVED, INFERRED, THIRD_PARTY_REPORTED, SELF_REPORTED,",
                   "`supports`: array of object", "`interfaces[].amount`: a number >= 0"):
        assert needle in text, needle


def test_order_like_schema_keeps_schema_order():
    doc = {"x_unmapped": [], "schema_version": "rwa-dd/2.1", "zzz": 1}
    assert list(schema.order_like_schema(doc)) == ["schema_version", "x_unmapped", "zzz"]
