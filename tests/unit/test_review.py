"""Test group 8: review packet (v0.5.0 section 5, v0.6.0 section 5, v0.7.0 section 5.1)."""

from test_support import GOLDEN, load_fixture
from lib import review, schema

SECTIONS = ["## Coverage", "## Section 1 preview", "## Portfolio components", "## Framework completeness",
            "## Three-layer chains", "## Amounts", "## Alternative paths", "## Conflicts", "## Provenance", "## QA",
            "## Migration checks pending", "## Material findings", "## Blocking gaps", "## Other gaps",
            "## Discrepancies", "## Scope unresolved", "## Unreconciled transactions", "## Structural changes",
            "## Issuer requests", "## Proposed next searches", "## Directives template"]


def test_review_matches_golden():
    expected = (GOLDEN / "acme.review.md").read_bytes().decode("utf-8")
    assert review.render(load_fixture(), 1) == expected


def test_review_is_deterministic():
    assert review.render(load_fixture(), 1) == review.render(load_fixture(), 1)


def test_sections_in_order():
    text = review.render(load_fixture(), 1)
    assert [line for line in text.split("\n") if line.startswith("## ")] == SECTIONS


def test_coverage_groups_and_flags():
    text = review.render(load_fixture(), 1)
    assert ("| group | CONFIRMED | SELF_REPORTED | THIRD_PARTY_REPORTED | INFERRED | UNRESOLVED | CONFLICTING |"
            in text)
    groups = [name for name in review.coverage(load_fixture())]
    assert groups == ["A layers and entities", "B L1->L2", "C L2->L3 and default", "D holder rights",
                      "E L3 business", "F flows", "O other", "S supports"]
    counts = review.coverage(load_fixture())
    assert counts["B L1->L2"]["CONFLICTING"] == 1  # X6.terms (D1)
    assert counts["E L3 business"]["THIRD_PARTY_REPORTED"] == 1
    assert counts["S supports"] == {"CONFIRMED": 0, "SELF_REPORTED": 4, "THIRD_PARTY_REPORTED": 0, "INFERRED": 0,
                                    "UNRESOLVED": 4, "CONFLICTING": 0}


def test_chains_and_requests_lines():
    text = review.render(load_fixture(), 1)
    assert ("- T2 Acme commodity trade finance: P2 holders -\\> \\[OTHER\\] -\\> E1 Acme Yield Issuer Ltd (L1/L2)"
            in text)
    assert "- **Q1** (priority 1) Security agreement and lien filings for the equipment loans -- " in text
    assert "(answers C2, C5)\n" in text


def test_empty_sections_print_none():
    doc = load_fixture()
    doc["findings"] = []
    doc["next_searches"] = []
    doc["issuer_requests"] = []
    doc["interfaces"] = []
    text = review.render(doc, 3)
    assert text.startswith("# Review packet acme round 3\n")
    assert text.count("\n- none\n") == 14
    assert "\n0 shown; 0 more open findings in section 6\n" in text
    assert "# no next searches proposed" in text


def _section(text, heading):
    start = text.index("## " + heading + "\n")
    end = text.find("\n## ", start + 1)
    return text[start:end]


def test_portfolio_amounts_and_alternatives():
    text = review.render(load_fixture(), 1)
    assert ("| T1 Acme equipment credit | CORE_CREDIT | DEPLOYED_VERIFIED [CONFIRMED] | P1 | 25000000 USDC"
            " CURRENT\\_BALANCE @2026-09-30 |") in \
        _section(text, "Portfolio components")
    assert "| T3 Acme treasury sleeve | LIQUIDITY_SLEEVE | -- [UNRESOLVED] | P2 | 5000000 USDC" in text
    amounts = _section(text, "Amounts")
    assert ("| strategy | interface | entry | kind | value | unit | basis | data as of | time basis | observed at |"
            " scope | counted | reason |") in amounts
    assert ("| T1 | X2 | 0 | L1_L2 | 25000000 | USDC | CURRENT_BALANCE | 2026-09-30T12:00:00Z | block |"
            " 2026-10-01T08:15:00Z |") in amounts
    assert ("| T1 | X2 | 2 | L1_L2 | 18000000 | USD | CUMULATIVE_FUNDED | 2026-06-30 | source | 2026-10-01T09:00:00Z |"
            " AUP loan sample: 12 loans funded 2026-01-01 to 2026-06-30 (S9); management figure, not tested | no |"
            " basis CUMULATIVE_FUNDED not counted |") in amounts
    assert ("| T3 | X10 | 0 | reserve_lookthrough | 5000000 | USD | RESERVE_LOOKTHROUGH | 2026-09-30 | source |"
            " 2026-10-01T08:30:00Z | Reserve assets of E11 backing the sleeve stablecoin | no | not a funding edge |"
            ) in amounts
    doc = load_fixture()
    doc["interfaces"][8]["amounts"][0]["as_of"] = None
    assert ("| T3 | X9 | 0 | sleeve_holding | 5000000 | USDC | CURRENT_BALANCE | not established | unresolved |"
            " 2026-10-01T08:30:00Z |") in _section(review.render(doc, 1), "Amounts")
    assert _section(text, "Alternative paths") == "## Alternative paths\n\n- A1 (T2): a X11; b X12\n"
    assert "| T3 Acme treasury sleeve |" not in _section(text, "Framework completeness")


def test_section1_preview_conflicts_provenance_qa():
    text = review.render(load_fixture(), 1)
    preview = _section(text, "Section 1 preview")
    assert "| id | type | material | blocking | k_checks | impact | statement |" in preview
    assert "| G1 | gap | yes | yes | K1 | capital_control, ownership | Issuer financial statements" in preview
    assert preview.endswith("\n4 shown; 2 more open findings in section 6\n")
    assert "| D1 | CONFLICTING | matched | open | X6.terms | S7, S1 |" in _section(text, "Conflicts")
    assert "| R1 | UNRECONCILED_TRANSACTION | matched | open | X13 | S8, S5 |" in _section(text, "Conflicts")
    assert _section(text, "Provenance").split("\n")[4:6] == [
        "| T1.l3\\_business.performance | verified | auditor_procedure | TESTED | S9 |",
        "| X2.amounts\\[2\\].value | self_reported | issuer_management | NOT_TESTED | S9 |"]
    assert "| id | rule | result | target | mapping | detail |" in _section(text, "QA")
    assert "| QA9 | placeholder | pass | -- | -- | ok |" in _section(text, "QA")
    results = [{"id": "E:a", "rule": "case a", "result": "fail", "detail": "R1: @G3 exists true -> false",
                "target": "R1", "legacy": "G3", "mapping": "legacy G3 -> R1 (carried_from G3)"}]
    assert ("| E:a | case a | fail | R1 | legacy G3 -\\> R1 (carried\\_from G3) | R1: @G3 exists true -\\> false |"
            in _section(review.render(load_fixture(), 1, results), "QA"))


def test_material_and_migration_sections():
    text = review.render(load_fixture(), 1)
    material = _section(text, "Material findings")
    assert material.count("\n- **") == 2 and "**G1**" in material and "**R1**" in material
    assert _section(text, "Migration checks pending") == "## Migration checks pending\n\n- none\n"
    assert "-- subjects: X4.security -- scope: Both describe the security" in _section(text, "Discrepancies")
    assert "**U1**" in _section(text, "Scope unresolved") and "-- subjects: Z1.coverage" in text
    assert "-- subjects: X13 -- scope: Both accounts concern" in _section(text, "Unreconciled transactions")
    doc = load_fixture()
    doc["findings"][3]["scope_note"] = schema.MIGRATED_NOTE_21 + " -- old note"
    doc["interfaces"][8]["amounts"][0]["scope"] = schema.MIGRATED_AMOUNT_SCOPE
    pending = _section(review.render(doc, 1), "Migration checks pending")
    assert "**D1**" in pending and "**D2**" not in pending
    assert ("- **X9.amounts[0]** CURRENT_BALANCE 5000000 USDC -- scope: unchecked (migrated from rwa-dd/2.1)"
            in pending)
    assert "| QA9 | placeholder | fail | -- | -- | D1, X9.amounts\\[0\\] |" in review.render(doc, 1)


def test_directives_template_accepts_u_and_r():
    text = review.render(load_fixture(), 1)
    assert "# answer G<k>|D<k>|U<k>|R<k> : <text>" in text and "# drop G<k>|D<k>|U<k>|R<k> : <reason>" in text
