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
    strategy.update({"id": "T1", "products": ["P1"]})
    doc["strategies"] = [strategy]
    assert validate.structural_errors(doc) == []
    assert doc["run"]["seeded_from"] is None and doc["schema_version"] == "rwa-dd/2.0"


def test_version_constants():
    assert (schema.SCHEMA_VERSION, schema.SKILL_VERSION) == ("rwa-dd/2.0", "0.5.1")


def test_subject_pattern_field_names():
    pattern = re.compile(schema.SUBJECT_PATTERN)
    for ok in ("T1.l3_business.performance", "P1.holder_rights.look_through", "X3.security", "E10"):
        assert pattern.match(ok), ok
    for bad in ("T1.3x", "T1.Field", "X1.a.b.c.d"):
        assert not pattern.match(bad), bad


def test_enums_contain_framework_values():
    e = schema.ENUMS
    for role in ("vault", "token_issuer", "protocol_operator", "holder_counterparty", "credit_manager",
                 "lender_of_record", "security_agent", "financing_recipient", "ultimate_obligor",
                 "receivables_seller", "asset_holding_spv", "guarantor", "issuer", "other"):
        assert role in e["role"]
    assert e["layer"] == ("L1", "L2", "L3")
    assert e["interface_kind"] == ("holder_L1", "L1_L2", "L2_L3", "within_L1", "within_L2", "within_L3")
    assert e["route_code"] == ("POOL", "FUND", "DIRECT", "WRAPPER")
    assert e["method_code"] == ("DL", "DI", "AP", "PI", "REPO", "PT")
    assert e["legal_class"] == ("DL", "DI", "AP", "PI", "FI", "EI", "OTHER")
    assert e["security"] == ("secured", "unsecured", "partially_secured")
    assert e["look_through"] == ("none", "via_security_trust", "via_spv", "direct_claim", "unresolved")
    assert e["business_type"] == ("private_credit", "trade_finance_pt", "mixed", "other")
    assert e["flow_view"] == ("settlement", "claim", "repayment")
    assert e["evidence_flag"] == ("CONFIRMED", "PARTIALLY_VERIFIED", "UNRESOLVED", "CONFLICTING")
    assert {"credit", "holder_rights", "business"} <= set(e["topic"])
    assert len(e["question_code"]) == 29 and e["question_code"][:2] == ("A1", "A2") and e["question_code"][-1] == "F3"
    assert "relationship_type" not in e


def test_document_key_order():
    assert schema.DOCUMENT.keys() == [
        "schema_version", "run", "project", "strategies", "sources", "entities", "interfaces", "holder_rights",
        "yield", "redemption", "eligibility", "audits", "size", "flows", "onchain", "history", "findings",
        "open_questions", "next_searches", "issuer_requests", "narrative", "x_unmapped"]
    assert schema.LEGAL_SECTIONS == ("entities", "interfaces", "holder_rights", "eligibility")


def test_order_like_schema_keeps_schema_order():
    doc = {"x_unmapped": [], "schema_version": "rwa-dd/2.0", "zzz": 1}
    assert list(schema.order_like_schema(doc)) == ["schema_version", "x_unmapped", "zzz"]
