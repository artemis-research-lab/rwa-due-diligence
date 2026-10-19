"""Test group 8: review packet (v0.5.0 section 5)."""

from test_support import GOLDEN, load_fixture
from lib import review

SECTIONS = ["## Coverage", "## Framework completeness", "## Three-layer chains", "## Blocking gaps",
            "## Other gaps", "## Discrepancies", "## Structural changes", "## Issuer requests",
            "## Proposed next searches", "## Directives template"]


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
    assert "| group | CONFIRMED | PARTIALLY_VERIFIED | UNRESOLVED | CONFLICTING |" in text
    groups = [name for name in review.coverage(load_fixture())]
    assert groups == ["A layers and entities", "B L1->L2", "C L2->L3 and default", "D holder rights",
                      "E L3 business", "F flows", "O other"]
    assert review.coverage(load_fixture())["C L2->L3 and default"]["CONFLICTING"] == 1


def test_chains_and_requests_lines():
    text = review.render(load_fixture(), 1)
    assert "- T2 Acme commodity trade finance: P2 holders -\\> \\[OTHER\\] -\\> E1 Acme Yield Issuer Ltd (L1)" in text
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
    assert text.count("\n- none\n") == 7
    assert "# no next searches proposed" in text
