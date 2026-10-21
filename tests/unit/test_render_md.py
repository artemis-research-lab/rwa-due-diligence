"""Test group 9: Markdown report (v0.6.0 section 6, v0.7.0 section 5.2: six reader sections, appendices A-O)."""

import copy

from test_support import GOLDEN, claim, load_fixture
from lib import render_md, schema

KEYS = ("T1-settlement", "T1-claim", "T1-repayment", "T2-settlement")
# Render clock date of the golden draft report (Report generated row).
TODAY = "2026-10-20"
SECTIONS = [
    "## 1. Executive summary and critical findings", "## 2. Framework completeness and portfolio",
    "## 3. Three-layer business model", "## 4. Capital allocation and credit deployment",
    "## 5. Holder rights, default and recovery", "## 6. Material gaps and issuer requests",
    "## Appendix A. Legal entity register", "## Appendix B. L3 business", "## Appendix C. Fund flows",
    "## Appendix D. Yield, fees and redemption", "## Appendix E. On-chain contracts and control",
    "## Appendix F. All findings", "## Appendix G. History", "## Appendix H. Audits and size",
    "## Appendix I. Sources", "## Appendix J. Analyst interventions", "## Appendix K. Unmapped facts",
    "## Appendix L. Legend"]
TAIL = ["## Appendix N. Quantitative and provenance checks", "## Appendix O. Changes"]


def _figures():
    return {key: (GOLDEN / ("acme.flow-%s.svg" % key)).read_bytes().decode("utf-8") for key in KEYS}


def test_report_matches_golden():
    expected = (GOLDEN / "acme.report.md").read_bytes().decode("utf-8")
    assert render_md.render(load_fixture(), (), _figures(), today=TODAY) == expected


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
    assert "GROSS_FUNDED" not in legend
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
    nf = claim()
    assert render_md.claim_cell(nf) == "-- [UNRESOLVED]"
    nf2 = dict(nf, evidence=["S2"], note="absent")
    assert render_md.claim_cell(nf2) == "-- [UNRESOLVED] (S2) -- absent"
    v = claim({"a": [1, "x"], "b": None}, "verified", ["S1", "S4"])
    assert render_md.claim_cell(v) == "a=1; x; b=-- [CONFIRMED] (S1, S4)"
    assert render_md.claim_cell(dict(v, status="inferred", note="n")) == "a=1; x; b=-- [INFERRED] (S1, S4) -- n"
    assert render_md.claim_cell(dict(v, status="third_party_reported")) == \
        "a=1; x; b=-- [THIRD_PARTY_REPORTED] (S1, S4)"
    assert render_md.claim_cell(dict(v, status="self_reported")) == "a=1; x; b=-- [SELF_REPORTED] (S1, S4)"
    assert render_md.claim_cell(v, "CONFLICTING") == "a=1; x; b=-- [CONFLICTING] (S1, S4)"
    q8 = claim(18000000, "self_reported", ["S9"], note="n", origin="issuer_management", assurance="NOT_TESTED")
    assert render_md.claim_cell(q8) == \
        "18000000 [SELF_REPORTED] (S9; origin issuer_management; assurance NOT_TESTED) -- n"
    assert render_md.claim_cell(claim("x", "inferred", [], note="n", origin="analyst")) == \
        "x [INFERRED] (origin analyst) -- n"


def test_conflicting_flag_in_report():
    text = render_md.render(load_fixture())
    assert "| No vault fee charged to P2 holders [CONFLICTING] (S1) |" in text
    assert "| secured [SELF_REPORTED] (S8) |" in text  # D2 is resolved
    assert ("(S5, S8) -- subjects: X4.security -- scope: Both describe the security of the X4 equipment loans as"
            " currently documented.\n") in text
    doc = load_fixture()
    doc["findings"] = [f for f in doc["findings"] if f["id"] != "D1"]
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
    assert headings == SECTIONS + TAIL
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
    assert d.rstrip("\n").endswith(lines[2])
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
    assert headings == SECTIONS + ["## Appendix M. Searches not run"] + TAIL


# --------------------------------------------------------------------------- v0.6.0 reader sections

def test_six_question_tables_for_credit_strategies():
    s1 = _section(render_md.render(load_fixture()), "1. Executive summary and critical findings")
    assert "### T1 Acme equipment credit\n\n| question | answer |\n|---|---|\n" in s1
    assert ("| Who holds investor capital? | E1 Acme Yield Issuer Ltd (L1) \\[SELF\\_REPORTED\\] |\n"
            "| Who deploys credit? | E5 Acme Credit Fund LP (L2) \\[SELF\\_REPORTED\\] |\n") in s1
    assert "| Who must repay? | E7 Example Equipment Lessors Ltd (L3)" in s1 and "cash flows from: E10 (L3-O)" in s1
    assert "| Who can enforce the claim? | UNRESOLVED |" in s1  # T2
    assert "| Is deployment verified? | DEPLOYED\\_VERIFIED \\[CONFIRMED\\] |" in s1
    assert "| Is deployment verified? | DISCLOSED\\_UNVERIFIED \\[SELF\\_REPORTED\\] |" in s1
    assert "### T3" not in s1
    doc = load_fixture()
    doc["strategies"][1]["component"] = "DEFI_LENDING"
    assert "### T2 Acme commodity trade finance" in render_md.render(doc)


def test_critical_findings_list_and_count_line():
    s1 = _section(render_md.render(load_fixture()), "1. Executive summary and critical findings")
    critical = s1[s1.index("### Critical findings"):].split("\n")
    assert critical[2:7] == [
        "- [MATERIAL] [ownership] **R1** (UNRECONCILED_TRANSACTION) The memorandum reports the X13 loans as sold to"
        " E13; the independent review still lists them on the E6 balance sheet. (S5, S8)",
        "- [MATERIAL] [BLOCKING] [K1] [capital_control, ownership] **G1** Issuer financial statements and the custody"
        " agreement are not public. (S8)",
        "- [BLOCKING] [K4] [security] **G3** The security agreement over the leased equipment is not public. (S8)",
        "- [BLOCKING] [security] **U1** (SCOPE_UNRESOLVED) The memorandum and the independent review may describe"
        " different coverage periods of the credit insurance. (S5, S8)",
        ""]
    assert critical[7] == ("4 critical findings shown (target 5-8; all material items are always shown). 2 further"
                           " open findings in section 6.")
    doc = load_fixture()
    doc["findings"][3].update({"material": True, "priority": 1})
    critical = _section(render_md.render(doc), "1. Executive summary and critical findings")
    assert "- [MATERIAL] **D1** (CONFLICTING) Archived docs" in critical
    assert "5 critical findings shown" in critical and ". 1 further open findings in section 6." in critical


def test_metadata_generated_and_observed_rows():
    text = render_md.render(load_fixture(), today="2026-10-20")
    assert ("| started | 2026-10-01T08:00:00Z |\n| finalized | -- |\n| Report generated | draft 2026-10-20 |\n"
            "| Data as of | 2026-06-30 to 2026-10-01 |\n| Sources retrieved | 2026-10-01T08:15:00Z to"
            " 2026-10-01T09:00:00Z |\n") in text
    assert "Data observed" not in text
    assert "| Report generated | draft |" in render_md.render(load_fixture())
    final = _final_doc()
    assert "| Report generated | 2026-10-02T00:00:00Z |" in render_md.render(final, today="2026-10-20")
    doc = load_fixture()
    for x in doc["interfaces"]:
        x["amounts"] = [a for a in x["amounts"] if a["as_of"] == "2026-08-15"]
    assert "| Data as of | 2026-08-15 |\n| Sources retrieved | 2026-10-01T08:40:00Z |" in render_md.render(doc)
    for x in doc["interfaces"]:
        x["amounts"] = []
    assert "| Data as of | n/d |\n| Sources retrieved | n/d |" in render_md.render(doc)


def test_portfolio_allocation_and_totals():
    s2 = _section(render_md.render(load_fixture()), "2. Framework completeness and portfolio")
    assert ("| T1 Acme equipment credit | CORE_CREDIT | DEPLOYED\\_VERIFIED [CONFIRMED] (S4; basis S4) -- Transfers"
            " from E1 into the E5 pool observed on-chain. | P1 |") in s2
    assert "| T3 Acme treasury sleeve | LIQUIDITY_SLEEVE | -- [UNRESOLVED] | P2 | -- [UNRESOLVED] |" in s2
    assert ("| T1 | X13 | 0 | asset_sale | 3000000 | USD | SALE_PROCEEDS | 2026-08-15 | source | 2026-10-01T08:40:00Z"
            " | Proceeds of the X13 loan sale to E13 | no | not a funding edge |") in s2
    assert "| strategy | T1 | 25000000 USDC CURRENT\\_BALANCE @2026-09-30 |" in s2
    assert ("| T1 | X2 | 1 | L1_L2 | 25150000 | USD | POSITION_VALUE | 2026-09-30 | source | 2026-10-01T08:40:00Z |"
            " E1 units in Acme Credit Fund LP | no | other measure of X2[0] |") in s2
    assert ("| strategy | interface | entry | kind | value | unit | basis | data as of | time basis | observed at |"
            " scope | counted | reason |") in s2
    assert "| product | P2 | 5000000 USDC CURRENT\\_BALANCE @2026-10-01 |" in s2
    assert s2.rstrip("\n").endswith("Totals add only amounts with the same basis, unit and data date; see"
                                    " Appendix N for the checks.")
    doc = load_fixture()
    doc["strategies"][2]["products"] = ["P1", "P2"]
    assert "@2026-10-01 (shared)" in _section(render_md.render(doc), "2. Framework completeness and portfolio")


def test_deployment_tables():
    s4 = _section(render_md.render(load_fixture()), "4. Capital allocation and credit deployment")
    assert [line for line in s4.split("\n") if line.startswith("### ")] == [
        "### L1 -> L2", "### L2 -> L3", "### Liquidity sleeves", "### Asset sales"]
    assert ("| id | strategy | from -> to | route | legal class | counterparty | instrument | claim holder | amounts |"
            " supply concentration | alternative | terms | governing law |") in s4
    assert ("| 25000000 USDC CURRENT_BALANCE data 2026-09-30T12:00:00Z (block) [CONFIRMED] (S4; basis S4); 25150000 USD"
            " POSITION_VALUE data 2026-09-30 (source) [SELF_REPORTED] (S8); 18000000 USD CUMULATIVE_FUNDED data"
            " 2026-06-30 (source) [SELF_REPORTED] (S9; origin issuer_management; assurance NOT_TESTED) | 0.5"
            " [CONFIRMED] (Pool shares held by E1 / Total pool share supply @2026-09-30T12:00:00Z, 20871234,"
            " ethereum) (S4; basis S4) |") in s4
    assert "\nAmount scopes:\n\n- X2[0]: USDC supplied by E1 to the E5 credit pool, read at the block\n" in s4
    assert "- X4[1]: Undrawn part of the E6 to E7 equipment loan facility\n" in s4
    assert "| X11 | T2 | E1 -\\> E9 (L2\\_L3) | REPO [SELF_REPORTED] (S7) |" in s4 and "| A1a |" in s4
    assert "| X8 | T1 | E7 -\\> E10 (L3\\_L3O) |" in s4
    assert ("| id | strategy | from -> to | loan identity | seller of record | buyer of record | legal transfer"
            " (title_transfer) | repayment source | servicer after exit (servicing) | recourse | retained exposure"
            " (residual_exposure) | amounts |") in s4
    assert ("| X13 | T1 | E6 -\\> E13 (asset\\_sale) | Equipment loan pool EQ-2026-A [INFERRED] (S8) -- Inferred"
            " from the sale schedule reference in the memorandum. | E6 Acme Warehouse SPV Ltd [SELF_REPORTED] (S8) |"
            " E13 Example Loan Buyer Fund [SELF_REPORTED] (S8) | true sale [SELF_REPORTED] (S8) | -- [UNRESOLVED]"
            " (S5) -- The independent review does not say who repays the buyer. |") in s4


def test_amount_cell():
    a = load_fixture()["interfaces"][1]["amounts"][1]
    assert render_md.amount_cell(a) == "25150000 USD POSITION_VALUE data 2026-09-30 (source) [SELF_REPORTED] (S8)"
    assert render_md.amount_cell(dict(a, as_of=None), "CONFLICTING") == \
        "25150000 USD POSITION_VALUE data not established (unresolved) [CONFLICTING] (S8)"
    assert render_md.amount_cell(dict(a, as_of="2026-09-30T12:00:00Z", block=1, chain="ethereum")) == \
        "25150000 USD POSITION_VALUE data 2026-09-30T12:00:00Z (block) [SELF_REPORTED] (S8)"


def test_supports_and_functions_tables():
    text = render_md.render(load_fixture())
    assert "| Z1 | CREDIT_ENHANCEMENT | T1 | E14 | E5 | Equipment loan principal [SELF_REPORTED] (S8) |" in text
    assert "| E10 | obligor_group | L3-O | contractual_obligor | T1 | S8 |" in text
    assert "| E11 | legal_person | -- | issuer | T3 | S7 |" in text


def test_section_6_open_findings_not_in_section_1():
    s6 = _section(render_md.render(load_fixture()), "6. Material gaps and issuer requests")
    assert [line for line in s6.split("\n") if line.startswith("### ")] == [
        "### Material", "### Blocking", "### Conflicts", "### Scope unresolved", "### Unreconciled transactions",
        "### Other gaps", "### Issuer requests"]
    assert ("- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7)\n"
            "  - scope: Both state the vault fee charged to P2 holders; S7 is the March 2026 version.\n"
            "  - scope match: matched\n"
            "  - assertion S7 (2026-03-15): Vault fee: 0.30 percent of assets per year.\n"
            "  - assertion S1 (2026-10-01): No fees are charged to vault holders.\n"
            "  - subjects: X6.terms\n"
            "  - resolution: open\n") in s6
    assert "**G2**" in s6 and "**G1**" not in s6 and "**R1**" not in s6 and "**D2**" not in s6
    doc = load_fixture()
    doc["findings"][6].update({"blocking": False, "impact": []})  # U1 leaves section 1
    s6 = _section(render_md.render(doc), "6. Material gaps and issuer requests")
    unresolved = s6[s6.index("### Scope unresolved"):s6.index("### Unreconciled transactions")]
    assert "**U1**" in unresolved and "  - assertion S5 (2026-07-15): Credit insurance covers 50 percent" in unresolved
    assert "  - assertion S8 (--): Credit insurance covers 90 percent of principal." in unresolved


def test_appendix_f_register_and_unreconciled():
    f = _section(render_md.render(load_fixture()), "Appendix F. All findings")
    assert ("| id | type | scope match | resolution | k_checks | impact | priority | carried from |\n|---|---|---|---|"
            "---|---|---|---|\n| C1 | structural_change | not_applicable | not_applicable | -- | -- | 3 | C1 |\n") in f
    assert "| R1 | unreconciled_transaction | matched | open | -- | ownership | 1 | G3 |" in f
    assert "| G3 | gap | not_applicable | open | K4 | security | 1 | -- |" in f
    assert "### Unreconciled transactions\n\n- **R1** [credit]" in f


def test_legend_bases_q8_conflicts_deployment():
    legend = _section(render_md.render(load_fixture()), "Appendix L. Legend")
    for name, meaning in schema.AMOUNT_BASIS_MEANINGS:
        assert "\n  - %s: %s.\n" % (name, meaning) in legend, name
    assert "- Counting rule: only CURRENT_BALANCE, POSITION_VALUE and OUTSTANDING_PRINCIPAL amounts" in legend
    assert "- Provenance (curator Q8): origin is who asserted the fact" in legend
    assert "stays SELF_REPORTED with assurance NOT_TESTED" in legend
    assert "- Conflict statuses of findings: CONFLICTING (open matched discrepancy), RESOLVED" in legend
    assert "- Deployment of a credit strategy: DEPLOYED_VERIFIED" in legend
    assert "R unreconciled transaction" in legend


def test_appendix_n_checks():
    n = _section(render_md.render(load_fixture()), "Appendix N. Quantitative and provenance checks")
    assert "| id | rule | result | target | mapping | detail |" in n
    assert "| QA1 | basis | pass | -- | -- | ok |" in n and "| QA11 | deployment | pass | -- | -- | ok |" in n
    assert "| QA4 | proceeds | pass | -- | -- | ok; unverified: X13.amounts\\[0\\] |" in n
    assert "| QA13 | timebasis | pass | -- | -- | ok |" in n
    assert "\nRules:\n\n- QA1 basis: No total mixes amount bases" in n
    results = [{"id": "E:x1", "rule": "case", "result": "fail", "detail": "X2: X2 exists true -> false",
                "target": "X2", "legacy": None, "mapping": ""},
               {"id": "E:x2", "rule": "legacy", "result": "pass", "detail": "R1: @G3 exists true -> true",
                "target": "R1", "legacy": "G3", "mapping": "legacy G3 -> R1 (carried_from G3)"}]
    n = _section(render_md.render(load_fixture(), qa_results=results), "Appendix N. Quantitative and provenance checks")
    assert "| E:x1 | case | fail | X2 | -- | X2: X2 exists true -\\> false |" in n and "| QA1 |" not in n
    assert ("| E:x2 | legacy | pass | R1 | legacy G3 -\\> R1 (carried\\_from G3) | R1: @G3 exists true -\\> true |"
            in n)


def test_appendix_o_changes():
    o = _section(render_md.render(load_fixture()), "Appendix O. Changes")
    assert o == "## Appendix O. Changes\n\nNo earlier run.\n"
    doc = load_fixture()
    doc["run"]["seeded_from"] = "acme-20260901T000000Z"
    rows = [{"ref": "G3 -> R1", "path": "type", "change": "changed", "before": "gap",
             "after": "unreconciled_transaction", "evidence_added": []},
            {"ref": "S9", "path": "", "change": "added", "before": None, "after": "AUP", "evidence_added": []}]
    o = _section(render_md.render(doc, change_rows=rows), "Appendix O. Changes since acme-20260901T000000Z")
    assert "| G3 -\\> R1 | type | changed | gap | unreconciled\\_transaction | -- |" in o
    assert "| S9 | -- | added | -- | AUP | -- |" in o
    assert _section(render_md.render(doc), "Appendix O. Changes since acme-20260901T000000Z").endswith("- none\n")
