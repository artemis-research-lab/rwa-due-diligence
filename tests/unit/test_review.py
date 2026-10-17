"""Test group 8: review packet."""

from test_support import GOLDEN, load_fixture
from lib import review


def test_review_matches_golden():
    expected = (GOLDEN / "acme.review.md").read_bytes().decode("utf-8")
    assert review.render(load_fixture(), 1) == expected


def test_review_is_deterministic():
    assert review.render(load_fixture(), 1) == review.render(load_fixture(), 1)


def test_empty_sections_print_none():
    doc = load_fixture()
    doc["findings"] = []
    doc["next_searches"] = []
    text = review.render(doc, 3)
    assert text.startswith("# Review packet acme round 3\n")
    assert text.count("\n- none\n") == 5
    assert "# no next searches proposed" in text
