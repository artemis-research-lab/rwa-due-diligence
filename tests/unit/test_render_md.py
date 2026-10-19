"""Test group 9: Markdown report (v0.5.0 section 6)."""

from test_support import GOLDEN, load_fixture
from lib import render_md

KEYS = ("T1-settlement", "T1-claim", "T1-repayment", "T2-settlement")


def _figures():
    return {key: (GOLDEN / ("acme.flow-%s.svg" % key)).read_bytes().decode("utf-8") for key in KEYS}


def test_report_matches_golden():
    expected = (GOLDEN / "acme.report.md").read_bytes().decode("utf-8")
    assert render_md.render(load_fixture(), (), _figures()) == expected


def test_interface_tables_have_counterparty_after_legal_class():
    text = render_md.render(load_fixture())
    assert "| id | strategy | from -> to | route | legal class | counterparty | instrument |" in text
    assert "| id | strategy | from -> to | method | legal class | counterparty | security |" in text


def test_legend_has_l3_o_line():
    text = render_md.render(load_fixture())
    assert ("\n- L3-O: the L3 business's paying customers or end borrowers (ultimate obligors), recorded as layer L3"
            " with role ultimate_obligor and linked by within_L3 interfaces.\n") in text


def test_render_twice_identical():
    assert render_md.render(load_fixture()) == render_md.render(load_fixture())


def test_free_text_is_escaped():
    doc = load_fixture()
    doc["project"]["name"]["value"] = "Acme | * _ <script>alert(1)</script>\nnext"
    doc["flows"]["edges"][0]["label"] = "a|b"
    doc["strategies"][0]["name"] = "T|<b>"
    text = render_md.render(doc)
    assert "# RWA Due Diligence: Acme \\| \\* \\_ \\<script\\>alert(1)\\</script\\> next\n" in text
    assert "<script>" not in text and "<b>" not in text
    assert "Acme | * _" not in text
    assert "| a\\|b |" in text
    assert "### T1 T\\|\\<b\\>\n" in text


def test_claim_cell_flags():
    nf = {"value": None, "status": "not_found", "evidence": [], "subject": None, "note": ""}
    assert render_md.claim_cell(nf) == "-- [UNRESOLVED]"
    nf2 = dict(nf, evidence=["S2"], note="absent")
    assert render_md.claim_cell(nf2) == "-- [UNRESOLVED] (S2) -- absent"
    v = {"value": {"a": [1, "x"], "b": None}, "status": "verified", "evidence": ["S1", "S4"], "subject": None,
         "note": ""}
    assert render_md.claim_cell(v) == "a=1; x; b=-- [CONFIRMED] (S1, S4)"
    assert render_md.claim_cell(dict(v, status="inferred", note="n")) == "a=1; x; b=-- [PARTIALLY_VERIFIED] (S1, S4) -- n"
    assert render_md.claim_cell(v, "CONFLICTING") == "a=1; x; b=-- [CONFLICTING] (S1, S4)"


def test_conflicting_flag_in_report():
    text = render_md.render(load_fixture())
    assert "| secured [CONFLICTING] (S8) |" in text
    assert "(S5, S8) -- subjects: X4.security\n" in text
    doc = load_fixture()
    doc["findings"] = [f for f in doc["findings"] if f["id"] != "D2"]
    assert "CONFLICTING]" not in render_md.render(doc)


def test_draft_banner_only_for_draft():
    doc = load_fixture()
    assert "> DRAFT -- not finalized\n" in render_md.render(doc)
    doc["run"].update({"status": "final", "finalized_at": "2026-10-02T00:00:00Z"})
    assert "DRAFT" not in render_md.render(doc)


def test_seeded_from_row():
    doc = load_fixture()
    assert "| seeded from |" not in render_md.render(doc)
    doc["run"]["seeded_from"] = "acme-20260901T000000Z"
    assert "| run id | acme-20261001T080000Z |\n| seeded from | acme-20260901T000000Z |\n| status |" in \
        render_md.render(doc)


def test_appendix_a_verbatim_with_safe_fence():
    rounds = [("Round 1", "accept N1\r\n# keep ``` here\n"), ("Round 2", "finalize\n")]
    text = render_md.render(load_fixture(), rounds)
    assert "### Round 1\n\n````text\naccept N1\n# keep ``` here\n````\n\n### Round 2\n\n```text\nfinalize\n```\n" \
        in text


def test_section_order():
    text = render_md.render(load_fixture())
    headings = [line for line in text.split("\n") if line.startswith("## ")]
    assert headings == [
        "## 1. Executive summary", "## 2. Framework completeness", "## 3. Three-layer functional map",
        "## 4. Legal entity register", "## 5. L1 -> L2 capital allocation", "## 6. L2 -> L3 underlying transactions",
        "## 7. Holder legal rights", "## 8. Default and recovery path", "## 9. L3 business",
        "## 10. Yield, fees and redemption", "## 11. Fund flows", "## 12. On-chain contracts and control",
        "## 13. Findings", "## 14. Issuer requests", "## 15. Audits and size", "## 16. History", "## 17. Sources",
        "## Appendix A. Analyst interventions", "## Appendix B. Unmapped facts", "## Appendix C. Legend"]
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_loss_waterfall_ordered_list():
    text = render_md.render(load_fixture())
    assert ("- Loss waterfall (1 absorbs first): [PARTIALLY_VERIFIED] (S8)\n  1. Borrower equity\n"
            "  2. Credit fund junior tranche\n  3. Senior noteholders\n") in text


def test_flow_image_links_only_with_figures():
    with_fig = render_md.render(load_fixture(), (), {"T2-settlement": "<svg/>"})
    assert ("### T2 Acme commodity trade finance -- settlement\n\n"
            "![Fund flow T2 settlement](acme.flow-T2-settlement.svg)\n\n| from |") in with_fig
    assert "![Fund flow T1" not in with_fig
    assert "![Fund flow" not in render_md.render(load_fixture())


def test_amendment_heading_and_metadata_row():
    rounds = [("Round 1", "accept N1\n"), ("Amendment 1 (reopens round 2)", "note fix\n"), ("Round 2", "finalize\n")]
    out = render_md.render(load_fixture(), rounds)
    assert "### Amendment 1 (reopens round 2)\n\n```text\nnote fix\n```" in out
    assert "| rounds | 1 |\n| amendments | 1 |\n| started |" in out
    assert "| amendments |" not in render_md.render(load_fixture(), [("Round 1", "accept N1\n")])


# --------------------------------------------------------------------------- v0.4.2 Appendix D, blocking gaps

def _final_doc():
    doc = load_fixture()
    doc["run"].update({"status": "final", "finalized_at": "2026-10-02T00:00:00Z"})
    return doc


def _section(text, heading):
    start = text.index("## " + heading + "\n")
    end = text.find("\n## ", start + 1)
    return text[start:] if end < 0 else text[start:end]


def test_blocking_gaps_marked_in_findings():
    s13 = _section(render_md.render(load_fixture()), "13. Findings")
    assert "- **G1** [legal] [BLOCKING] Issuer financial statements" in s13
    assert "- **G2** [yield] Gross yield" in s13
    assert "  - **N1**" in s13


def test_final_findings_have_no_search_lines():
    s13 = _section(render_md.render(_final_doc()), "13. Findings")
    assert "[BLOCKING]" in s13 and "**N" not in s13


def test_final_appendix_d_marks_rejected():
    text = render_md.render(_final_doc(), (), None, {"N1"})
    d = _section(text, "Appendix D. Searches not run")
    lines = [line for line in d.split("\n") if line.startswith("- ")]
    assert [line[:8] for line in lines] == ["- **N1**", "- **N2**", "- **N3**"]
    assert lines[0].endswith("(resolves G1; est 6 calls) -- rejected by the analyst")
    assert lines[1].endswith("(resolves G2, D1; est 4 calls) -- not run")
    assert text.rstrip("\n").endswith(lines[2])
    plain = _section(render_md.render(_final_doc()), "Appendix D. Searches not run")
    assert "rejected by the analyst" not in plain and plain.count(" -- not run") == 3


def test_final_appendix_d_empty_and_draft_has_none():
    doc = _final_doc()
    doc["next_searches"] = []
    assert _section(render_md.render(doc), "Appendix D. Searches not run") == \
        "## Appendix D. Searches not run\n\n- none\n"
    assert "Appendix D" not in render_md.render(load_fixture(), (), None, {"N1"})
