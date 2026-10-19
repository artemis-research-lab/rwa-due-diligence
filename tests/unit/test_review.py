"""Test group 8: review packet (v0.5.0 section 5, v0.6.0 section 5)."""

from test_support import GOLDEN, load_fixture
from lib import review, schema

SECTIONS = ["## Coverage", "## Portfolio components", "## Framework completeness", "## Three-layer chains",
            "## Allocation", "## Alternative paths", "## Material findings", "## Scope checks pending",
            "## Blocking gaps", "## Other gaps", "## Discrepancies", "## Scope unresolved", "## Structural changes",
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
    assert counts["C L2->L3 and default"]["CONFLICTING"] == 1
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
    assert text.count("\n- none\n") == 12
    assert "# no next searches proposed" in text


def _section(text, heading):
    start = text.index("## " + heading + "\n")
    end = text.find("\n## ", start + 1)
    return text[start:end]


def test_portfolio_allocation_and_alternatives():
    text = review.render(load_fixture(), 1)
    assert "| T1 Acme equipment credit | CORE_CREDIT | P1 | 25000000 n/d |" in _section(text, "Portfolio components")
    assert "| T3 Acme treasury sleeve | LIQUIDITY_SLEEVE | P2 | 5000000 USD |" in text
    allocation = _section(text, "Allocation")
    assert "| T1 | X2 | L1_L2 | 25000000 | GROSS_FUNDED | yes | counted |" in allocation
    assert "| T3 | X10 | reserve_lookthrough | 5000000 USD | LOOKTHROUGH | no | basis LOOKTHROUGH |" in allocation
    assert _section(text, "Alternative paths") == "## Alternative paths\n\n- A1 (T2): a X11; b X12\n"
    assert "| T3 Acme treasury sleeve |" not in _section(text, "Framework completeness")


def test_material_and_scope_sections():
    text = review.render(load_fixture(), 1)
    assert _section(text, "Material findings").count("\n- **") == 1 and "**G1**" in _section(text, "Material findings")
    assert _section(text, "Scope checks pending") == "## Scope checks pending\n\n- none\n"
    assert "-- subjects: X4.security -- scope: Both describe the security" in _section(text, "Discrepancies")
    assert "**U1**" in _section(text, "Scope unresolved") and "-- subjects: Z1.coverage" in text
    doc = load_fixture()
    doc["findings"][3]["scope_note"] = schema.MIGRATED_SCOPE_NOTE
    pending = _section(review.render(doc, 1), "Scope checks pending")
    assert "**D1**" in pending and "**D2**" not in pending
