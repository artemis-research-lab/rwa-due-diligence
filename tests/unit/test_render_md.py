"""Test group 9: Markdown report (v0.6.0 section 6: six reader sections, appendices A-M)."""

from test_support import GOLDEN, load_fixture
from lib import render_md

KEYS = ("T1-settlement", "T1-claim", "T1-repayment", "T2-settlement")
SECTIONS = [
    "## 1. Executive summary and critical findings", "## 2. Framework completeness and portfolio",
    "## 3. Three-layer business model", "## 4. Capital allocation and credit deployment",
    "## 5. Holder rights, default and recovery", "## 6. Material gaps and issuer requests",
    "## Appendix A. Legal entity register", "## Appendix B. L3 business", "## Appendix C. Fund flows",
    "## Appendix D. Yield, fees and redemption", "## Appendix E. On-chain contracts and control",
    "## Appendix F. All findings", "## Appendix G. History", "## Appendix H. Audits and size",
    "## Appendix I. Sources", "## Appendix J. Analyst interventions", "## Appendix K. Unmapped facts",
    "## Appendix L. Legend"]


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
    assert ("\n- L3-O: optional sub-layer of parties downstream of L3 whose payments repay it; roles"
            " contractual_obligor (a document shows they legally owe L3), cash_flow_source (business cash flows) and"
            " offtaker_customer (buyers of goods, services or compute); linked by L3_L3O interfaces.\n") in text


def test_legend_has_six_flags():
    legend = _section(render_md.render(load_fixture()), "Appendix L. Legend")
    for flag in ("CONFIRMED", "SELF_REPORTED", "THIRD_PARTY_REPORTED", "INFERRED", "UNRESOLVED", "CONFLICTING"):
        assert "\n- %s: " % flag in legend, flag
    assert "\n- SELF_REPORTED: stated by the issuer, protocol, borrower or another interested party.\n" in legend
    assert "\n- THIRD_PARTY_REPORTED: reported by a third party; its scope and authority still need assessing.\n" \
        in legend
    assert "PROTOCOL_ENTITLEMENT" in legend and "Counting rule" in legend and "`alt A1a`" in legend
    assert "[S] SELF_REPORTED, [T] THIRD_PARTY_REPORTED, [I] INFERRED" in legend


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
    assert render_md.claim_cell(dict(v, status="inferred", note="n")) == "a=1; x; b=-- [INFERRED] (S1, S4) -- n"
    assert render_md.claim_cell(dict(v, status="third_party_reported")) == "a=1; x; b=-- [THIRD_PARTY_REPORTED] (S1, S4)"
    assert render_md.claim_cell(dict(v, status="self_reported")) == "a=1; x; b=-- [SELF_REPORTED] (S1, S4)"
    assert render_md.claim_cell(v, "CONFLICTING") == "a=1; x; b=-- [CONFLICTING] (S1, S4)"


def test_conflicting_flag_in_report():
    text = render_md.render(load_fixture())
    assert "| secured [CONFLICTING] (S8) |" in text
    assert ("(S5, S8) -- subjects: X4.security -- scope: Both describe the security of the X4 equipment loans as"
            " currently documented.\n") in text
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
    assert headings == SECTIONS
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_loss_waterfall_ordered_list():
    text = render_md.render(load_fixture())
    assert ("- Loss waterfall (1 absorbs first): [SELF_REPORTED] (S8)\n  1. Borrower equity\n"
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


# --------------------------------------------------------------------------- v0.4.2 Appendix M, blocking gaps

def _final_doc():
    doc = load_fixture()
    doc["run"].update({"status": "final", "finalized_at": "2026-10-02T00:00:00Z"})
    return doc


def _section(text, heading):
    start = text.index("## " + heading + "\n")
    end = text.find("\n## ", start + 1)
    return text[start:] if end < 0 else text[start:end]


def test_blocking_gaps_marked_in_findings():
    s13 = _section(render_md.render(load_fixture()), "Appendix F. All findings")
    assert "- **G1** [legal] [MATERIAL] [BLOCKING] Issuer financial statements" in s13
    assert "- **G2** [yield] Gross yield" in s13
    assert "  - **N1**" in s13


def test_final_findings_have_no_search_lines():
    s13 = _section(render_md.render(_final_doc()), "Appendix F. All findings")
    assert "[BLOCKING]" in s13 and "**N" not in s13


def test_final_appendix_m_marks_rejected():
    text = render_md.render(_final_doc(), (), None, {"N1"})
    d = _section(text, "Appendix M. Searches not run")
    lines = [line for line in d.split("\n") if line.startswith("- ")]
    assert [line[:8] for line in lines] == ["- **N1**", "- **N2**", "- **N3**"]
    assert lines[0].endswith("(resolves G1; est 6 calls) -- rejected by the analyst")
    assert lines[1].endswith("(resolves G2, D1; est 4 calls) -- not run")
    assert text.rstrip("\n").endswith(lines[2])
    plain = _section(render_md.render(_final_doc()), "Appendix M. Searches not run")
    assert "rejected by the analyst" not in plain and plain.count(" -- not run") == 3


def test_final_appendix_m_empty_and_draft_has_none():
    doc = _final_doc()
    doc["next_searches"] = []
    assert _section(render_md.render(doc), "Appendix M. Searches not run") == \
        "## Appendix M. Searches not run\n\n- none\n"
    assert "Appendix M" not in render_md.render(load_fixture(), (), None, {"N1"})


def test_final_section_order_ends_with_appendix_m():
    headings = [line for line in render_md.render(_final_doc()).split("\n") if line.startswith("## ")]
    assert headings == SECTIONS + ["## Appendix M. Searches not run"]


# --------------------------------------------------------------------------- v0.6.0 reader sections

def test_five_question_tables_for_core_credit_only():
    s1 = _section(render_md.render(load_fixture()), "1. Executive summary and critical findings")
    assert "### T1 Acme equipment credit\n\n| question | answer |\n|---|---|\n" in s1
    assert ("| Who holds investor capital? | E1 Acme Yield Issuer Ltd (L1) \\[SELF\\_REPORTED\\] |\n"
            "| Who deploys credit? | E5 Acme Credit Fund LP (L2) \\[SELF\\_REPORTED\\] |\n") in s1
    assert "| Who must repay? | E7 Example Equipment Lessors Ltd (L3)" in s1 and "cash flows from: E10 (L3-O)" in s1
    assert "| Who can enforce the claim? | UNRESOLVED |" in s1  # T2
    assert "### T3" not in s1


def test_critical_findings_material_then_blocking():
    s1 = _section(render_md.render(load_fixture()), "1. Executive summary and critical findings")
    critical = s1[s1.index("### Critical findings"):]
    assert critical.split("\n")[2:4] == [
        "- **G1** [legal] [MATERIAL] [BLOCKING] Issuer financial statements and the custody agreement are not"
        " public. (S8)",
        "- **G3** [credit] [BLOCKING] Perfection of the security interest over the leased equipment is not"
        " evidenced. (S8)"]
    doc = load_fixture()
    doc["findings"][3]["material"] = True
    critical = _section(render_md.render(doc), "1. Executive summary and critical findings")
    assert "- **D1** [yield] [MATERIAL] Archived docs" in critical


def test_portfolio_and_allocation_tables():
    s2 = _section(render_md.render(load_fixture()), "2. Framework completeness and portfolio")
    assert "| T3 Acme treasury sleeve | LIQUIDITY_SLEEVE | P2 | -- [UNRESOLVED] | 5000000 USD |" in s2
    assert "| T1 | X13 | asset_sale | 3000000 USD | SALE_PROCEEDS | no | basis SALE_PROCEEDS |" in s2
    assert "| T3 Acme treasury sleeve | CONFIRMED" not in s2


def test_deployment_tables():
    s4 = _section(render_md.render(load_fixture()), "4. Capital allocation and credit deployment")
    assert [line for line in s4.split("\n") if line.startswith("### ")] == [
        "### L1 -> L2", "### L2 -> L3", "### Liquidity sleeves", "### Asset sales"]
    assert ("| id | strategy | from -> to | route | legal class | counterparty | instrument | claim holder | amount |"
            " basis | supply concentration | alternative | terms | governing law |") in s4
    assert "| X11 | T2 | E1 -\\> E9 (L2\\_L3) | REPO [SELF_REPORTED] (S7) |" in s4 and "| A1a |" in s4
    assert "| X8 | T1 | E7 -\\> E10 (L3\\_L3O) |" in s4
    assert "| X13 | T1 | E6 -\\> E13 (asset\\_sale) | true sale [SELF_REPORTED] (S8) |" in s4


def test_supports_and_functions_tables():
    text = render_md.render(load_fixture())
    assert "| Z1 | CREDIT_ENHANCEMENT | T1 | E14 | E5 | Equipment loan principal [SELF_REPORTED] (S8) |" in text
    assert "| E10 | obligor_group | L3-O | contractual_obligor | T1 | S8 |" in text
    assert "| E11 | legal_person | -- | issuer | T3 | S7 |" in text


def test_section_6_lists_gaps_scope_and_discrepancies():
    s6 = _section(render_md.render(load_fixture()), "6. Material gaps and issuer requests")
    assert [line for line in s6.split("\n") if line.startswith("### ")] == [
        "### Material and blocking gaps", "### Scope unresolved", "### Discrepancies", "### Issuer requests"]
    assert "**G2**" not in s6 and "**U1**" in s6 and "-- scope: Both state the vault fee" in s6
