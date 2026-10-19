"""Markdown report renderer (section 3.8, v0.6.0 section 6: six reader sections, detail in appendices A-M);
deterministic, adds only fixed headings, labels and the legend."""

import json

from lib import flow, framework, review, schema
from lib.textutil import finding_line, id_key, md_text, not_run_suffix, request_line, search_line, totals_text

NONE = "- none"


# --------------------------------------------------------------------------- cells

def fmt_value(value):
    if value is None:
        return "--"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        return md_text(value, schema.CLAIM_VALUE_STR_MAX)
    if isinstance(value, list):
        return "; ".join(fmt_value(v) for v in value)
    if isinstance(value, dict):
        return "; ".join("%s=%s" % (md_text(k), fmt_value(v)) for k, v in value.items())
    return md_text(str(value))


def _tail(claim, flag):
    cell = "[%s]" % flag
    if claim["evidence"]:
        cell += " (%s)" % ", ".join(claim["evidence"])
    if claim["note"]:
        cell += " -- " + md_text(claim["note"], schema.CLAIM_NOTE_MAX)
    return cell


def claim_cell(claim, flag=None):
    """`<value> [FLAG] (S1, S4) -- note`; flag defaults to the one derived from the status alone."""
    flag = framework.flag(claim, False) if flag is None else flag
    return "%s %s" % (fmt_value(claim["value"]), _tail(claim, flag))


def text(value, limit=None):
    return "--" if value is None else md_text(value, limit)


def table(header, rows):
    if not rows:
        return [NONE]
    out = ["| %s |" % " | ".join(header), "|" + "---|" * len(header)]
    out += ["| %s |" % " | ".join(row) for row in rows]
    return out


def product_title(product):
    name = product["name"]["value"]
    return product["id"] if name is None else "%s %s" % (product["id"], fmt_value(name))


def strategy_title(strategy):
    return "%s %s" % (strategy["id"], md_text(strategy["name"], 80)) if strategy["name"] else strategy["id"]


class _Cells:
    """claim_cell with the document's derived flags (conflicts included)."""

    def __init__(self, doc):
        by_parts = framework.flags(doc)
        self.by_id = {id(claim): by_parts[parts] for parts, claim in schema.iter_claims(doc)}

    def flag(self, claim):
        return self.by_id.get(id(claim))

    def __call__(self, claim):
        return claim_cell(claim, self.flag(claim))


def _alt(x):
    tag = framework.alt_tag(x)
    return "--" if tag is None else tag


# --------------------------------------------------------------------------- metadata

def _metadata(doc, rounds=()):
    run = doc["run"]
    rows = [
        ("slug", text(run["slug"])),
        ("root URL", text(run["root_url"], 500)),
        ("run id", text(run["run_id"])),
        ("status", run["status"]),
        ("rounds", str(run["round"])),
        ("started", text(run["started_at"])),
        ("finalized", text(run["finalized_at"])),
        ("skill version", text(run["skill_version"])),
        ("schema version", text(doc["schema_version"])),
    ]
    amendments = sum(1 for heading, _ in rounds if heading.startswith("Amendment "))
    if amendments:
        rows.insert(5, ("amendments", str(amendments)))
    if run.get("seeded_from") is not None:
        rows.insert(3, ("seeded from", text(run["seeded_from"], 64)))
    return table(("field", "value"), [list(r) for r in rows])


# --------------------------------------------------------------------------- 1. executive summary

def _critical(doc):
    """Material findings, then blocking gaps not already listed; each with its markers."""
    findings = sorted(doc["findings"], key=id_key)
    out = []
    for f in findings:
        if f["material"]:
            blocking = "[BLOCKING] " if f["type"] == "gap" and f["blocking"] else ""
            out.append(finding_line(f, marker="[MATERIAL] " + blocking))
    out += [finding_line(f, marker="[BLOCKING] ") for f in findings
            if f["type"] == "gap" and f["blocking"] and not f["material"]]
    return out


def _executive(doc):
    out = []
    if doc["narrative"]["executive_summary"]:
        out += [md_text(doc["narrative"]["executive_summary"], 800), ""]
    for t in framework.core_strategies(doc):
        out += ["### " + strategy_title(t), ""]
        out += table(("question", "answer"), [[q, md_text(a)] for q, a in framework.five_questions(doc, t["id"])])
        out.append("")
    out += ["### Critical findings", ""]
    return out + (_critical(doc) or [NONE])


# --------------------------------------------------------------------------- 2. completeness and portfolio

def _completeness(doc):
    names = {t["id"]: t for t in doc["strategies"]}
    return table(["strategy"] + ["%s %s" % (code, label) for code, label in framework.CHECKS],
                 [[strategy_title(names[sid])] + [fl for _, _, fl in checks]
                  for sid, checks in framework.completeness(doc)])


def _portfolio(doc, cell):
    totals = framework.allocation_totals(doc)["strategies"]
    out = ["### Completeness", ""] + _completeness(doc)
    out += ["", "### Portfolio components", ""]
    out += table(("strategy", "component", "products", "business type", "counted total"),
                 [[strategy_title(t), t["component"], ", ".join(sorted(t["products"], key=id_key)),
                   cell(t["business_type"]), totals_text(totals.get(t["id"], {}))]
                  for t in sorted(doc["strategies"], key=id_key)])
    out += ["", "### Allocation", ""]
    return out + (review.allocation_table(doc) or [NONE])


# --------------------------------------------------------------------------- 3. three-layer business model

def _functional_map(doc, cell):
    out = []
    for t in sorted(doc["strategies"], key=id_key):
        out += ["### " + strategy_title(t), "",
                "- Component: " + t["component"],
                "- Products: " + ", ".join(sorted(t["products"], key=id_key)),
                "- Business type: " + cell(t["business_type"]),
                "- Sublayers: " + (md_text(t["sublayers"], 200) if t["sublayers"] else "--"),
                "- Chains:"]
        lines = framework.chain_line(doc, t["id"])
        out += ["  - " + md_text(line) for line in lines] or ["  - none"]
        out.append("")
    rows = [[e["id"], e["entity_class"], text(fn["layer"]), fn["role"], text(fn["strategy"]),
             ", ".join(fn["evidence"])]
            for e in sorted(doc["entities"], key=id_key) for fn in e["functions"]]
    out += ["### Functions by entity", ""]
    return out + table(("entity", "class", "layer", "role", "strategy", "evidence"), rows)


# --------------------------------------------------------------------------- 4. allocation and deployment

def _interfaces(doc, kinds):
    return [x for x in sorted(doc["interfaces"], key=id_key) if x["kind"] in kinds]


def _ends(x):
    return "%s -> %s (%s)" % (x["from"], x["to"], x["kind"])


def _deployment(doc, cell):
    out = ["### L1 -> L2", ""]
    out += table(("id", "strategy", "from -> to", "route", "legal class", "counterparty", "instrument",
                  "claim holder", "amount", "basis", "supply concentration", "alternative", "terms",
                  "governing law"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["route"]), cell(x["legal_class"]),
                   cell(x["counterparty"]), cell(x["instrument"]), cell(x["claim_holder"]), cell(x["amount"]),
                   x["amount_basis"] or "--", cell(x["supply_concentration"]), _alt(x), cell(x["terms"]),
                   cell(x["governing_law"])]
                  for x in _interfaces(doc, ("holder_L1", "L1_L2", "within_L1"))])
    out += ["", "### L2 -> L3", ""]
    out += table(("id", "strategy", "from -> to", "method", "legal class", "counterparty", "security",
                  "collateral", "perfection", "enforcement", "recourse", "amount", "alternative", "terms"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["method"]), cell(x["legal_class"]),
                   cell(x["counterparty"]), cell(x["security"]), cell(x["collateral"]), cell(x["perfection"]),
                   cell(x["enforcement"]), cell(x["recourse"]), cell(x["amount"]), _alt(x), cell(x["terms"])]
                  for x in _interfaces(doc, ("L2_L3", "within_L2", "within_L3", "L3_L3O"))])
    out += ["", "### Liquidity sleeves", ""]
    out += table(("id", "strategy", "from -> to", "legal class", "instrument", "amount", "basis", "terms"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["legal_class"]), cell(x["instrument"]),
                   cell(x["amount"]), x["amount_basis"] or "--", cell(x["terms"])]
                  for x in _interfaces(doc, ("sleeve_holding", "reserve_lookthrough"))])
    out += ["", "### Asset sales", ""]
    out += table(("id", "strategy", "from -> to", "title transfer", "servicing", "recourse", "amount", "basis",
                  "residual exposure"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["title_transfer"]), cell(x["servicing"]),
                   cell(x["recourse"]), cell(x["amount"]), x["amount_basis"] or "--", cell(x["residual_exposure"])]
                  for x in _interfaces(doc, ("asset_sale",))])
    return out


# --------------------------------------------------------------------------- 5. holder rights, default, supports

HOLDER_FIELDS = (("instrument_nature", "Instrument nature"), ("claim_against", "Claim against"),
                 ("look_through", "Look-through"), ("recourse", "Recourse"), ("governing_law", "Governing law"),
                 ("forum", "Forum"), ("insolvency_protection", "Insolvency protection"),
                 ("disclaimers", "Disclaimers"))
DEFAULT_FIELDS = (("events_of_default", "Events of default"), ("enforcement", "Enforcement"))
L3_FIELDS = (("description", "Description"), ("revenue_model", "Revenue model"),
             ("cash_generation", "Cash generation"), ("collections_control", "Collections control"),
             ("concentration", "Concentration"), ("performance", "Performance"),
             ("operating_history", "Operating history"))
SUPPORT_FIELDS = ("covered_exposure", "trigger", "coverage", "exclusions", "priority", "enforceability",
                  "governing_law", "holder_recourse")


def _holder_rights(doc, cell):
    out = []
    for p in sorted(doc["project"]["products"], key=id_key):
        out += ["### Holder rights: " + product_title(p), ""]
        entries = [h for h in doc["holder_rights"] if h["product"] == p["id"]]
        out += ["- %s: %s" % (label, cell(h[field])) for h in entries for field, label in HOLDER_FIELDS] or [NONE]
        out.append("")
    return out


def _waterfall(claim, cell):
    label = "- Loss waterfall (1 absorbs first): "
    value = claim["value"]
    if isinstance(value, list) and value:
        return [label + _tail(claim, cell.flag(claim))] + [
            "  %d. %s" % (i, fmt_value(item)) for i, item in enumerate(value, start=1)]
    return [label + cell(claim)]


def _default_path(doc, cell):
    out = []
    for t in framework.core_strategies(doc):
        path = t["default_path"]
        out += ["### Default and recovery: " + strategy_title(t), ""]
        out += ["- %s: %s" % (label, cell(path[field])) for field, label in DEFAULT_FIELDS]
        out += _waterfall(path["loss_waterfall"], cell)
        out += ["- Recovery history: " + cell(path["recovery_history"]), ""]
    return out


def _supports(doc, cell):
    out = ["### Supports", ""]
    return out + table(("id", "type", "strategies", "provider", "beneficiary", "covered exposure", "trigger",
                        "coverage", "exclusions", "priority", "enforceability", "governing law", "holder recourse"),
                       [[z["id"], z["type"], ", ".join(z["strategies"]), z["provider"], text(z["beneficiary"])]
                        + [cell(z[field]) for field in SUPPORT_FIELDS]
                        for z in sorted(doc["supports"], key=id_key)])


def _rights_default(doc, cell):
    return _holder_rights(doc, cell) + _default_path(doc, cell) + _supports(doc, cell)


# --------------------------------------------------------------------------- 6. material gaps and requests

def _gaps_requests(doc):
    findings = sorted(doc["findings"], key=id_key)
    gaps = []
    for f in findings:
        if f["type"] == "gap" and (f["material"] or f["blocking"]):
            marker = ("[MATERIAL] " if f["material"] else "") + ("[BLOCKING] " if f["blocking"] else "")
            gaps.append(finding_line(f, marker=marker))
    out = ["### Material and blocking gaps", ""] + (gaps or [NONE])
    out += ["", "### Scope unresolved", ""]
    out += [finding_line(f, subjects=True) for f in findings if f["type"] == "scope_unresolved"] or [NONE]
    out += ["", "### Discrepancies", ""]
    out += [finding_line(f, subjects=True, scope=True) for f in findings if f["type"] == "discrepancy"] or [NONE]
    out += ["", "### Issuer requests", ""]
    return out + ([request_line(q) for q in sorted(doc["issuer_requests"], key=id_key)] or [NONE])


# --------------------------------------------------------------------------- appendices

def _register(doc, cell):
    entities = sorted(doc["entities"], key=id_key)
    out = table(("entity", "class", "legal name", "jurisdiction", "type", "registration", "licence status"),
                [[e["id"], e["entity_class"], cell(e["legal_name"]), cell(e["jurisdiction"]),
                  cell(e["entity_type"]), cell(e["registration_id"]), cell(e["license_status"])] for e in entities])
    licenses = [[e["id"], cell(lic["regulator"]), cell(lic["license_type"]), cell(lic["license_id"]),
                 cell(lic["status"])] for e in entities for lic in e["licenses"]]
    if licenses:
        out += ["", "Licences:", ""]
        out += table(("entity", "regulator", "licence type", "licence id", "licence status"), licenses)
    return out


def _l3_business(doc, cell):
    out = []
    for t in framework.core_strategies(doc):
        out += ["### " + strategy_title(t), ""]
        out += ["- %s: %s" % (label, cell(t["l3_business"][field])) for field, label in L3_FIELDS]
        out.append("")
    return out


def _yield(doc, cell):
    out = []
    for p in sorted(doc["project"]["products"], key=id_key):
        out += ["### Yield " + product_title(p), ""]
        entries = [y for y in doc["yield"] if y["product"] == p["id"]]
        if not entries:
            out += [NONE, ""]
        for y in entries:
            out += [
                "- Mechanism: " + cell(y["mechanism"]),
                "- Gross yield: " + cell(y["gross_yield"]),
                "- Net yield to holder: " + cell(y["net_yield_to_holder"]),
                "- Distribution method: " + cell(y["distribution"]["method"]),
                "- Distribution frequency: " + cell(y["distribution"]["frequency"]),
                "",
                "Underlying:",
                "",
            ]
            out += table(("description", "asset class", "share pct", "location"),
                         [[cell(u["description"]), cell(u["asset_class"]), cell(u["share_pct"]),
                           cell(u["location"])] for u in y["underlying"]])
            out += ["", "Fees:", ""]
            out += table(("type", "rate", "recipient"),
                         [[cell(f["type"]), cell(f["rate"]), cell(f["recipient"])] for f in y["fees"]])
            out.append("")
    out += ["### Redemption", ""]
    out += table(("product", "mechanism", "queue", "settlement time", "gating", "fees"),
                 [[r["product"], cell(r["mechanism"]), cell(r["queue"]), cell(r["settlement_time"]),
                   cell(r["gating"]), cell(r["fees"])]
                  for r in sorted(doc["redemption"], key=lambda r: id_key(r["product"]))])
    out += ["", "### Eligibility", ""]
    out += table(("product", "restrictions"),
                 [[e["product"], cell(e["restrictions"])]
                  for e in sorted(doc["eligibility"], key=lambda e: id_key(e["product"]))])
    return out


def _flows(doc, figures, cell):
    nodes = {n["id"]: n for n in doc["flows"]["nodes"]}

    def node_cell(nid):
        node = nodes.get(nid)
        return nid if node is None else "%s %s" % (nid, md_text(node["label"], 40))

    out = ["Nodes:", ""]
    out += table(("id", "label", "lane", "layer", "kind", "chain", "ref"),
                 [[n["id"], md_text(n["label"], 40), n["lane"], text(n["layer"]), n["kind"], text(n["chain"], 24),
                   text(n["ref"])] for n in sorted(doc["flows"]["nodes"], key=id_key)])
    for t in sorted(doc["strategies"], key=id_key):
        for view in flow.VIEWS:
            key = "%s-%s" % (t["id"], view)
            out += ["", "### %s -- %s" % (strategy_title(t), view), ""]
            if key in figures:
                out += ["![Fund flow %s %s](%s.flow-%s.svg)" % (t["id"], view, doc["run"]["slug"], key), ""]
            out += table(("from", "to", "kind", "mechanism", "rail", "interface", "label", "claim"),
                         [[node_cell(e["from"]), node_cell(e["to"]), e["kind"], e["mechanism"], e["rail"],
                           text(e["interface"]), md_text(e["label"], 40), cell(e["claim"])]
                          for _, e in flow.view_edges(doc, t["id"], view)])
    return out


def _onchain(doc, cell):
    rows = []
    for c in doc["onchain"]["contracts"]:
        ctl = c["control"]
        ms = ctl["multisig"]
        rows.append([text(c["chain"], 24), text(c["address"], 64), cell(c["role"]), cell(c["source_verified"]),
                     cell(c["proxy"]), cell(ctl["upgrade_admin"]), cell(ctl["role_admins"]),
                     cell(ctl["timelock_delay_s"]), cell(ms["address"]), cell(ms["threshold"]),
                     cell(ms["signers_count"])])
    return table(("chain", "address", "role", "source verified", "proxy", "upgrade admin", "role admins",
                  "timelock delay s", "multisig", "threshold", "signers"), rows)


def _findings(doc):
    """Gaps (markers; a draft nests the searches that resolve blocking gaps), discrepancies with subjects and
    scope notes, scope unresolved, structural changes and open questions."""
    findings = sorted(doc["findings"], key=id_key)
    searches = [] if doc["run"]["status"] == "final" else sorted(doc["next_searches"], key=id_key)
    gaps = []
    for f in findings:
        if f["type"] != "gap":
            continue
        marker = ("[MATERIAL] " if f["material"] else "") + ("[BLOCKING] " if f["blocking"] else "")
        gaps.append(finding_line(f, marker=marker))
        if f["blocking"]:
            gaps += ["  " + search_line(n) for n in searches if f["id"] in n["resolves"]]
    out = ["### Gaps", ""] + (gaps or [NONE])
    out += ["", "### Discrepancies", ""]
    out += [finding_line(f, subjects=True, scope=True) for f in findings if f["type"] == "discrepancy"] or [NONE]
    out += ["", "### Scope unresolved", ""]
    out += [finding_line(f, subjects=True) for f in findings if f["type"] == "scope_unresolved"] or [NONE]
    out += ["", "### Structural changes", ""]
    out += [finding_line(f) for f in findings if f["type"] == "structural_change"] or [NONE]
    out += ["", "### Open questions", ""]
    out += ["- [%s] %s" % (q["topic"], md_text(q["question"], 200)) for q in doc["open_questions"]] or [NONE]
    return out


def _not_run(doc, rejected):
    return [search_line(n, not_run_suffix(n, rejected)) for n in sorted(doc["next_searches"], key=id_key)]


def _audits_size(doc, cell):
    out = ["### Audits", ""]
    out += table(("auditor", "scope", "date", "report"),
                 [[cell(a["auditor"]), cell(a["scope"]), cell(a["date"]), text(a["report_ref"])]
                  for a in doc["audits"]])
    out += ["", "### Size", ""]
    out += table(("product", "metric", "value", "as of"),
                 [[text(s["product"]), s["metric"], cell(s["value"]), text(s["as_of"])] for s in doc["size"]])
    return out


def _history(doc):
    return table(("date", "change", "evidence"),
                 [[text(h["date"]), md_text(h["change"], 200), ", ".join(h["evidence"])] for h in doc["history"]])


def _sources(doc):
    rows = []
    for s in sorted(doc["sources"], key=id_key):
        fetch = s["fetch"]
        if s["archived"]:
            if fetch != "archived":
                fetch += ", archived"
            fetch += " (version %s)" % text(s["version_date"])
        rows.append([s["id"], s["source_type"], s["origin"], fetch, text(s["retrieved_at"]),
                     "%s -- %s" % (md_text(s["title"], 200), md_text(s["url"], 500)), md_text(s["note"], 200)])
    return table(("id", "type", "origin", "fetch", "retrieved", "title/url", "note"), rows)


def _fence(body):
    longest = run = 0
    for ch in body:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    return "`" * max(3, longest + 1)


def _interventions(rounds):
    out = []
    for heading, body in rounds:
        body = body.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
        fence = _fence(body)
        out += ["### " + heading, "", fence + "text"] + body.split("\n") + [fence, ""]
    return out


def _unmapped(doc):
    out = []
    for x in doc["x_unmapped"]:
        line = "- " + md_text(x["fact"], 200)
        if x["evidence"]:
            line += " (%s)" % ", ".join(x["evidence"])
        out.append(line + " -- why unmapped: " + md_text(x["why_unmapped"], 120))
    return out


LEGEND = [
    "- Claim cell: `value [FLAG] (evidence) -- note`; `--` means no value.",
    "- CONFIRMED: direct, sufficient evidence for the precise claim within its stated scope (legal facts:"
    " regulator, registry, auditor or on-chain sources only).",
    "- SELF_REPORTED: stated by the issuer, protocol, borrower or another interested party.",
    "- THIRD_PARTY_REPORTED: reported by a third party; its scope and authority still need assessing.",
    "- INFERRED: the analyst's conclusion from cited facts; the note states the reasoning.",
    "- UNRESOLVED: not found in the cited sources, or not searched when no source is cited.",
    "- CONFLICTING: named by a discrepancy finding about the same fact, timeframe and scope (see Appendix F);"
    " scope-unresolved findings never make a claim CONFLICTING.",
    "- Layers are functions inside one strategy, by position in its financing chain: L1 on-chain capital vault;"
    " L2 credit financing layer; L3 underlying business layer.",
    "- L3-O: optional sub-layer of parties downstream of L3 whose payments repay it; roles contractual_obligor"
    " (a document shows they legally owe L3), cash_flow_source (business cash flows) and offtaker_customer"
    " (buyers of goods, services or compute); linked by L3_L3O interfaces.",
    "- Route (L1->L2): POOL supply to a shared lending pool; FUND subscription to a fund or vehicle; DIRECT financing"
    " of the credit counterparty itself; WRAPPER a position in another vault or token that holds the exposure.",
    "- Method (L2->L3): DL direct loan; DI debt instrument (note, bond); AP purchase of receivables or other"
    " assets; PI participation interest; REPO repurchase agreement; PT principal purchase and resale (trade"
    " finance); OTHER other method.",
    "- Legal class: DL loan claim; DI debt instrument claim; AP ownership of purchased assets; PI participation"
    " interest; FI fund interest; EI equity interest; PROTOCOL_ENTITLEMENT a pool receipt or other"
    " protocol-enforced entitlement; OTHER other or contractual claim.",
    "- Components: CORE_CREDIT an underlying real-world financing business; LIQUIDITY_SLEEVE undeployed cash or"
    " stablecoin (issuer and reserves, no L3); DEFI_LENDING lending-market supply with protocol-enforced"
    " entitlements.",
    "- Amount bases: GROSS_FUNDED funded principal; COMMITMENT committed, not necessarily funded; LOOKTHROUGH"
    " exposure seen through a held instrument; RESERVE reserve assets of an issuer; SALE_PROCEEDS proceeds of"
    " an asset sale.",
    "- Counting rule: only GROSS_FUNDED amounts on L1_L2 and sleeve_holding interfaces outside alternative groups"
    " are counted; everything else is linked, not summed.",
    "- Alternative tag: `alt A1a` marks option a of alternative group A1, competing legal paths for one position;"
    " they are never parallel exposures and are not counted.",
    "- Flow views: settlement (capital and asset movement); claim (legal rights and collateral);"
    " repayment (cash back to L2 and L1, fees, enforcement path).",
    "- Lanes: offchain, boundary (conversion, bridge and custody hand-off points), onchain.",
    "- Diagram suffixes: [C] CONFIRMED, [S] SELF_REPORTED, [T] THIRD_PARTY_REPORTED, [I] INFERRED,"
    " [U] UNRESOLVED ([U?] not searched), [X] CONFLICTING.",
    "- Findings: G gap, D discrepancy, U scope unresolved, C structural change; issuer requests Q cite the research"
    " question codes they answer. No risk scores are given.",
]


def render(doc, rounds=(), figures=None, rejected=()):
    """Render a structurally valid document; rounds = [(heading, text), ...];
    figures = {"T<n>-<view>": SVG text}: a figure gets an image link to <slug>.flow-T<n>-<view>.svg;
    rejected = N ids the analyst rejected, marked in Appendix M (final reports only)."""
    figures = figures or {}
    cell = _Cells(doc)
    name = doc["project"]["name"]["value"]
    title = doc["run"]["slug"] if name is None else fmt_value(name)
    lines = ["# RWA Due Diligence: " + title, ""]
    lines += _metadata(doc, rounds)
    if doc["run"]["status"] == "draft":
        lines += ["", "> DRAFT -- not finalized"]

    sections = (
        ("1. Executive summary and critical findings", _executive(doc)),
        ("2. Framework completeness and portfolio", _portfolio(doc, cell)),
        ("3. Three-layer business model", _functional_map(doc, cell)),
        ("4. Capital allocation and credit deployment", _deployment(doc, cell)),
        ("5. Holder rights, default and recovery", _rights_default(doc, cell)),
        ("6. Material gaps and issuer requests", _gaps_requests(doc)),
        ("Appendix A. Legal entity register", _register(doc, cell)),
        ("Appendix B. L3 business", _l3_business(doc, cell)),
        ("Appendix C. Fund flows", _flows(doc, figures, cell)),
        ("Appendix D. Yield, fees and redemption", _yield(doc, cell)),
        ("Appendix E. On-chain contracts and control", _onchain(doc, cell)),
        ("Appendix F. All findings", _findings(doc)),
        ("Appendix G. History", _history(doc)),
        ("Appendix H. Audits and size", _audits_size(doc, cell)),
        ("Appendix I. Sources", _sources(doc)),
        ("Appendix J. Analyst interventions", _interventions(rounds)),
        ("Appendix K. Unmapped facts", _unmapped(doc)),
        ("Appendix L. Legend", LEGEND),
    )
    if doc["run"]["status"] == "final":
        sections += (("Appendix M. Searches not run", _not_run(doc, rejected)),)
    for heading, body in sections:
        while body and body[-1] == "":
            body = body[:-1]
        lines += ["", "## " + heading, ""]
        lines += body or [NONE]
    return "\n".join(lines).rstrip("\n") + "\n"
