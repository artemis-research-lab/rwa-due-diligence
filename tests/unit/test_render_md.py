"""Test group 9: Markdown report."""

from test_support import GOLDEN, load_fixture
from lib import render_md


def _figures():
    return {pid: (GOLDEN / ("acme.flow-%s.svg" % pid)).read_bytes().decode("utf-8") for pid in ("P1", "P2")}


def test_report_matches_golden():
    expected = (GOLDEN / "acme.report.md").read_bytes().decode("utf-8")
    assert render_md.render(load_fixture(), (), _figures()) == expected


def test_render_twice_identical():
    assert render_md.render(load_fixture()) == render_md.render(load_fixture())


def test_free_text_is_escaped():
    doc = load_fixture()
    doc["project"]["name"]["value"] = "Acme | * _ <script>alert(1)</script>\nnext"
    doc["flows"]["edges"][0]["label"] = "a|b"
    text = render_md.render(doc)
    assert "# RWA Due Diligence: Acme \\| \\* \\_ \\<script\\>alert(1)\\</script\\> next\n" in text
    assert "<script>" not in text
    assert "Acme | * _" not in text
    assert "| a\\|b |" in text


def test_claim_cell_markers():
    nf = {"value": None, "status": "not_found", "evidence": [], "subject": None, "note": ""}
    assert render_md.claim_cell(nf) == "-- [N?]"
    nf2 = dict(nf, evidence=["S2"], note="absent")
    assert render_md.claim_cell(nf2) == "-- [N] (S2) -- absent"
    v = {"value": {"a": [1, "x"], "b": None}, "status": "verified", "evidence": ["S1", "S4"], "subject": None,
         "note": ""}
    assert render_md.claim_cell(v) == "a=1; x; b=-- [V] (S1, S4)"


def test_draft_banner_only_for_draft():
    doc = load_fixture()
    assert "> DRAFT -- not finalized\n" in render_md.render(doc)
    doc["run"].update({"status": "final", "finalized_at": "2026-10-02T00:00:00Z"})
    assert "DRAFT" not in render_md.render(doc)


def test_appendix_a_verbatim_with_safe_fence():
    rounds = [("Round 1", "accept N1\r\n# keep ``` here\n"), ("Round 2", "finalize\n")]
    text = render_md.render(load_fixture(), rounds)
    assert "### Round 1\n\n````text\naccept N1\n# keep ``` here\n````\n\n### Round 2\n\n```text\nfinalize\n```\n" \
        in text


def test_section_order():
    text = render_md.render(load_fixture())
    headings = [line for line in text.split("\n") if line.startswith("## ")]
    assert headings == [
        "## 1. Executive summary", "## 2. Blocking gaps and materials to request", "## 3. Products",
        "## 4. Legal structure", "## 5. Yield source", "## 6. Fund flows", "## 7. On-chain contracts and control",
        "## 8. Redemption and eligibility", "## 9. Audits", "## 10. Size", "## 11. History", "## 12. Findings",
        "## 13. Open questions", "## 14. Sources", "## Appendix A. Analyst interventions",
        "## Appendix B. Unmapped facts", "## Appendix C. Legend"]
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_flow_image_links_only_with_figures():
    with_fig = render_md.render(load_fixture(), (), {"P2": "<svg/>"})
    assert "### P2 Acme Treasury Vault\n\n![Fund flow P2](acme.flow-P2.svg)\n\n| from |" in with_fig
    assert "![Fund flow P1]" not in with_fig
    assert "![Fund flow" not in render_md.render(load_fixture())

def test_amendment_heading_and_metadata_row():
    rounds = [("Round 1", "accept N1\n"), ("Amendment 1 (reopens round 2)", "note fix\n"), ("Round 2", "finalize\n")]
    out = render_md.render(load_fixture(), rounds)
    assert "### Amendment 1 (reopens round 2)\n\n```text\nnote fix\n```" in out
    assert "| rounds | 1 |\n| amendments | 1 |\n| started |" in out
    assert "| amendments |" not in render_md.render(load_fixture(), [("Round 1", "accept N1\n")])


# --------------------------------------------------------------------------- v0.4.2 Appendix D

def _final_doc():
    doc = load_fixture()
    doc["run"].update({"status": "final", "finalized_at": "2026-10-02T00:00:00Z"})
    return doc


def _section(text, heading):
    start = text.index("## " + heading + "\n")
    end = text.find("\n## ", start + 1)
    return text[start:] if end < 0 else text[start:end]


def test_final_section_2_has_no_search_lines():
    s2 = _section(render_md.render(_final_doc()), "2. Blocking gaps and materials to request")
    assert "**G1**" in s2 and "**N" not in s2
    assert "  - **N1**" in _section(render_md.render(load_fixture()), "2. Blocking gaps and materials to request")


def test_final_appendix_d_marks_rejected():
    text = render_md.render(_final_doc(), (), None, {"N1"})
    d = _section(text, "Appendix D. Searches not run")
    lines = [line for line in d.split("\n") if line.startswith("- ")]
    assert [line[:8] for line in lines] == ["- **N1**", "- **N2**"]
    assert lines[0].endswith("(resolves G1; est 6 calls) -- rejected by the analyst")
    assert lines[1].endswith("(resolves G2, D1; est 4 calls) -- not run")
    assert text.rstrip("\n").endswith(lines[1])
    plain = _section(render_md.render(_final_doc()), "Appendix D. Searches not run")
    assert "rejected by the analyst" not in plain and plain.count(" -- not run") == 2


def test_final_appendix_d_empty_and_draft_has_none():
    doc = _final_doc()
    doc["next_searches"] = []
    assert _section(render_md.render(doc), "Appendix D. Searches not run") == \
        "## Appendix D. Searches not run\n\n- none\n"
    assert "Appendix D" not in render_md.render(load_fixture(), (), None, {"N1"})