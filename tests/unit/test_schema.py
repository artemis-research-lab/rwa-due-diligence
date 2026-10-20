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
    assert doc["run"]["seeded_from"] is None and doc["schema_version"] == "rwa-dd/2.2"
    assert doc["supports"] == []
    interface = schema.skeleton(schema.INTERFACE)
    assert interface["alternative"] == {"group": None, "option": None} and interface["amounts"] == []
    assert interface["supply_concentration"] == {"ratio": schema.empty_claim(), "numerator": "", "denominator": "",
                                                 "as_of": None, "block": None, "chain": None}
    support = schema.skeleton(schema.SUPPORT)
    support.update({"id": "Z1", "type": "YIELD_SUPPORT", "strategies": ["T1"], "provider": "E1"})
    assert validate.structural_errors(support, schema.SUPPORT) == []


def test_version_constants():
    assert (schema.SCHEMA_VERSION, schema.SKILL_VERSION) == ("rwa-dd/2.2", "0.7.0")
    assert schema.MIGRATED_SCOPE_NOTE == "unchecked (migrated from rwa-dd/2.0)"
    assert schema.MIGRATED_NOTE_21 == schema.MIGRATED_AMOUNT_SCOPE == "unchecked (migrated from rwa-dd/2.1)"
    assert schema.MIGRATION_PLACEHOLDERS == (schema.MIGRATED_SCOPE_NOTE, schema.MIGRATED_NOTE_21)
    assert schema.ISSUER_ORIGINS == ("issuer_management", "issuer_documents", "borrower")
    assert schema.SECTION1_IMPACTS == ("capital_control", "ownership", "redemption", "enforcement", "security")


def test_subject_pattern_field_names():
    pattern = re.compile(schema.SUBJECT_PATTERN)
    for ok in ("T1.l3_business.performance", "P1.holder_rights.look_through", "X3.security", "E10", "Z1.coverage",
               "X2.amounts[0].value", "X4.supply_concentration.ratio", "E2.licenses[0].regulator", "X1.a.b.c.d"):
        assert pattern.match(ok), ok
    for bad in ("T1.3x", "T1.Field", "X1.a.b.c.d.e", "U1.coverage", "X2.amounts[x]", "X2[0]", "X2.amounts[0]x"):
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
    assert e["amount_basis"] == ("CURRENT_BALANCE", "POSITION_VALUE", "OUTSTANDING_PRINCIPAL", "CUMULATIVE_FUNDED",
                                 "FACILITY_COMMITMENT", "UNDRAWN_COMMITMENT", "SALE_PROCEEDS", "RESERVE_LOOKTHROUGH",
                                 "OTHER")
    assert e["assertion_origin"] == ("issuer_management", "issuer_documents", "borrower", "regulator", "registry",
                                     "onchain", "independent_party", "auditor_procedure", "analyst")
    assert e["assurance_scope"] == ("TESTED", "NOT_TESTED", "NOT_APPLICABLE")
    assert e["deployment"] == ("DEPLOYED_VERIFIED", "DISCLOSED_UNVERIFIED", "NOT_DEPLOYED", "UNRESOLVED")
    assert e["scope_match"] == ("matched", "not_matched", "unchecked", "not_applicable")
    assert e["resolution_status"] == ("open", "resolved", "not_applicable")
    assert e["k_check"] == ("K1", "K2", "K3", "K4", "K5", "K6", "K7")
    assert e["impact"] == ("credit_exposure", "investor_rights", "governance", "capital_control", "ownership",
                           "redemption", "enforcement", "security", "recovery", "liquidity")
    assert e["entity_class"] == ("legal_person", "contract_or_pool", "program", "obligor_group", "unknown")
    assert e["support_type"] == ("CREDIT_ENHANCEMENT", "YIELD_SUPPORT")
    assert e["claim_status"] == ("verified", "self_reported", "third_party_reported", "inferred", "not_found")
    assert e["finding_type"] == ("gap", "discrepancy", "structural_change", "scope_unresolved",
                                 "unreconciled_transaction")
    assert schema.FINDING_PREFIX["scope_unresolved"] == "U"
    assert schema.FINDING_PREFIX["unreconciled_transaction"] == "R"
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


def test_2_2_document_shape():
    fields = dict(schema.DOCUMENT.fields)
    assert schema.STRATEGY.keys()[:6] == ["id", "products", "name", "component", "business_type", "deployment"]
    assert fields["entities"].item.keys()[:2] == ["id", "entity_class"]
    functions = dict(fields["entities"].item.fields)["functions"].item
    assert dict(functions.fields)["layer"].nullable
    keys = schema.INTERFACE.keys()
    assert keys[keys.index("recourse") + 1:] == ["alternative", "amounts", "supply_concentration", "title_transfer",
                                                 "servicing", "residual_exposure", "loan_identity",
                                                 "seller_of_record", "buyer_of_record", "repayment_source", "as_of"]
    assert schema.AMOUNT.keys() == ["basis", "value", "unit", "as_of", "block", "chain", "scope", "valuation_basis"]
    amount = dict(schema.AMOUNT.fields)
    assert amount["unit"].max_len == 20 and amount["scope"].max_len == 200 and amount["valuation_basis"].nullable
    assert amount["block"].describe() == "integer >=0 | null" and amount["as_of"].kind == "date_or_timestamp"
    assert schema.SUPPLY_CONCENTRATION.keys() == ["ratio", "numerator", "denominator", "as_of", "block", "chain"]
    assert schema.SUPPORT.keys() == ["id", "type", "strategies", "provider", "beneficiary", "covered_exposure",
                                     "trigger", "coverage", "exclusions", "priority", "enforceability",
                                     "governing_law", "holder_recourse"]
    finding = fields["findings"].item
    assert finding.keys() == ["id", "type", "topic", "blocking", "material", "statement", "scope_note", "scope_match",
                              "evidence", "subjects", "assertions", "resolution", "k_checks", "impact", "priority",
                              "carried_from"]
    parts = dict(finding.fields)
    assert parts["assertions"].item.keys() == ["source", "statement", "as_of"]
    assert parts["resolution"].keys() == ["status", "note"]
    assert parts["priority"].describe() == "integer 1..3" and parts["carried_from"].nullable
    assert re.match(parts["id"].regex, "R1") and re.match(parts["carried_from"].regex, "U9")
    resolves = dict(fields["next_searches"].item.fields)["resolves"].item
    assert all(re.match(resolves.regex, x) for x in ("G1", "D2", "U3", "R1")) and not re.match(resolves.regex, "C1")
    assert ("interfaces", "amount") not in schema.CODED_CLAIMS
    assert schema.CODED_CLAIMS[("interfaces", "value")] == (None, "number")
    assert schema.CODED_CLAIMS[("interfaces", "ratio")] == (None, "ratio")
    assert schema.CODED_CLAIMS[("strategies", "deployment")] == ("deployment", "one")
    node_layer = dict(dict(fields["flows"].fields)["nodes"].item.fields)["layer"]
    assert re.match(node_layer.regex, "L3-O") and not re.match(node_layer.regex, "L4")


def test_claim_keys_and_empty_claim():
    assert schema.CLAIM_KEYS == ("value", "status", "evidence", "subject", "note", "origin", "assurance")
    assert list(schema.empty_claim()) == list(schema.CLAIM_KEYS)
    assert schema.empty_claim()["origin"] is None and schema.empty_claim()["assurance"] is None


def test_date_or_timestamp_and_nullable_int():
    node = schema.DateOrTimestamp(nullable=True)
    assert node.describe() == "date YYYY-MM-DD or timestamp YYYY-MM-DDTHH:MM:SSZ | null"
    for ok in ("2026-10-20", "2026-10-20T23:59:59Z", None):
        assert validate.structural_errors(ok, node) == [], ok
    assert validate.structural_errors("2026-02-30", node) == [": not a real date_or_timestamp"]
    assert validate.structural_errors("2026-10-20T25:00:00Z", node) == [": not a real date_or_timestamp"]
    assert validate.structural_errors("2026-10-20T10:00Z", node) == [
        ": must be date YYYY-MM-DD or timestamp YYYY-MM-DDTHH:MM:SSZ"]
    assert validate.structural_errors(None, schema.DateOrTimestamp()) == [": must not be null"]
    block = schema.Int(0, nullable=True)
    assert validate.structural_errors(None, block) == [] and validate.structural_errors(-1, block) == [
        ": out of range (integer >=0 | null)"]
    assert validate.structural_errors(None, schema.Int(1, 3)) == [": must not be null"]
    assert schema.Int(1, 3, nullable=True).describe() == "integer 1..3 | null"


def test_schema_doc_documents_2_2():
    text = schema.schema_doc()
    assert text.startswith("# Schema rwa-dd/2.2\n")
    for needle in ("third_party_reported", "THIRD_PARTY_REPORTED", "unreconciled_transaction=R", "Counting rule",
                   "`P<n>.holder_rights.<field>`", "`X2.amounts[0].value`", schema.MIGRATED_SCOPE_NOTE,
                   schema.MIGRATED_NOTE_21, "`origin`: enum assertion_origin | null", "`assurance`: enum",
                   "Severity (worst first): CONFLICTING, UNRESOLVED, INFERRED, THIRD_PARTY_REPORTED, SELF_REPORTED,",
                   "`supports`: array of object", "`interfaces[].amounts[].value`: a number >= 0",
                   "`interfaces[].supply_concentration.ratio`: a number 0..1", "SCOPE_UNRESOLVED",
                   "UNRECONCILED_TRANSACTION", "## Quality checks (dd.py qa)", "QA11 deployment",
                   "## Derived output", "rwa-dd-derived/1", "`record_sha256`", "not_contains",
                   "`CUMULATIVE_FUNDED`: actual disbursements over a stated period."):
        assert needle in text, needle
    assert "GROSS_FUNDED" not in text


def test_order_like_schema_keeps_schema_order():
    doc = {"x_unmapped": [], "schema_version": "rwa-dd/2.2", "zzz": 1}
    assert list(schema.order_like_schema(doc)) == ["schema_version", "x_unmapped", "zzz"]
