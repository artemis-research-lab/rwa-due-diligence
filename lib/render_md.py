"""Markdown report renderer (section 3.8, v0.5 section 6); deterministic, adds only fixed headings, labels and
the legend."""

import json

from lib import flow, framework, schema
from lib.textutil import finding_line, id_key, md_text, not_run_suffix, request_line, search_line

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


# --------------------------------------------------------------------------- sections

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


def _completeness(doc):
    names = {t["id"]: t for t in doc["strategies"]}
    return table(["strategy"] + ["%s %s" % (code, label) for code, label in framework.CHECKS],
                 [[strategy_title(names[sid])] + [fl for _, _, fl in checks]
                  for sid, checks in framework.completeness(doc)])


def _functional_map(doc, cell):
    out = []
    for t in sorted(doc["strategies"], key=id_key):
        out += ["### " + strategy_title(t), "",
                "- Products: " + ", ".join(sorted(t["products"], key=id_key)),
                "- Business type: " + cell(t["business_type"]),
                "- Sublayers: " + (md_text(t["sublayers"], 200) if t["sublayers"] else "--"),
                "- Chains:"]
        lines = framework.chain_line(doc, t["id"])
        out += ["  - " + md_text(line) for line in lines] or ["  - none"]
        out.append("")
    rows = [[e["id"], fn["layer"], fn["role"], text(fn["strategy"]), ", ".join(fn["evidence"])]
            for e in sorted(doc["entities"], key=id_key) for fn in e["functions"]]
    out += ["### Functions by entity", ""]
    return out + table(("entity", "layer", "role", "strategy", "evidence"), rows)


def _register(doc, cell):
    entities = sorted(doc["entities"], key=id_key)
    out = table(("entity", "legal name", "jurisdiction", "type", "registration", "licence status"),
                [[e["id"], cell(e["legal_name"]), cell(e["jurisdiction"]), cell(e["entity_type"]),
                  cell(e["registration_id"]), cell(e["license_status"])] for e in entities])
    licenses = [[e["id"], cell(lic["regulator"]), cell(lic["license_type"]), cell(lic["license_id"]),
                 cell(lic["status"])] for e in entities for lic in e["licenses"]]
    if licenses:
        out += ["", "Licences:", ""]
        out += table(("entity", "regulator", "licence type", "licence id", "licence status"), licenses)
    return out


def _interfaces(doc, kinds):
    return [x for x in sorted(doc["interfaces"], key=id_key) if x["kind"] in kinds]


def _ends(x):
    return "%s -> %s (%s)" % (x["from"], x["to"], x["kind"])


def _l1_l2(doc, cell):
    return table(("id", "strategy", "from -> to", "route", "legal class", "instrument", "claim holder", "terms",
                  "governing law"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["route"]), cell(x["legal_class"]),
                   cell(x["instrument"]), cell(x["claim_holder"]), cell(x["terms"]), cell(x["governing_law"])]
                  for x in _interfaces(doc, ("holder_L1", "L1_L2", "within_L1"))])


def _l2_l3(doc, cell):
    return table(("id", "strategy", "from -> to", "method", "legal class", "security", "collateral", "perfection",
                  "enforcement", "recourse", "terms"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["method"]), cell(x["legal_class"]),
                   cell(x["security"]), cell(x["collateral"]), cell(x["perfection"]), cell(x["enforcement"]),
                   cell(x["recourse"]), cell(x["terms"])]
                  for x in _interfaces(doc, ("L2_L3", "within_L2", "within_L3"))])


HOLDER_FIELDS = (("instrument_nature", "Instrument nature"), ("claim_against", "Claim against"),
                 ("look_through", "Look-through"), ("recourse", "Recourse"), ("governing_law", "Governing law"),
                 ("forum", "Forum"), ("insolvency_protection", "Insolvency protection"),
                 ("disclaimers", "Disclaimers"))
DEFAULT_FIELDS = (("events_of_default", "Events of default"), ("enforcement", "Enforcement"))
L3_FIELDS = (("description", "Description"), ("revenue_model", "Revenue model"),
             ("cash_generation", "Cash generation"), ("collections_control", "Collections control"),
             ("concentration", "Concentration"), ("performance", "Performance"),
             ("operating_history", "Operating history"))


def _holder_rights(doc, cell):
    out = []
    for p in sorted(doc["project"]["products"], key=id_key):
        out += ["### " + product_title(p), ""]
        entries = [h for h in doc["holder_rights"] if h["product"] == p["id"]]
        out += ["- %s: %s" % (label, cell(h[field])) for h in entries for field, label in HOLDER_FIELDS] or [NONE]
        out.append("")
    return out[:-1]


def _waterfall(claim, cell):
    label = "- Loss waterfall (1 absorbs first): "
    value = claim["value"]
    if isinstance(value, list) and value:
        return [label + _tail(claim, cell.flag(claim))] + [
            "  %d. %s" % (i, fmt_value(item)) for i, item in enumerate(value, start=1)]
    return [label + cell(claim)]


def _default_path(doc, cell):
    out = []
    for t in sorted(doc["strategies"], key=id_key):
        path = t["default_path"]
        out += ["### " + strategy_title(t), ""]
        out += ["- %s: %s" % (label, cell(path[field])) for field, label in DEFAULT_FIELDS]
        out += _waterfall(path["loss_waterfall"], cell)
        out += ["- Recovery history: " + cell(path["recovery_history"]), ""]
    return out[:-1]


def _l3_business(doc, cell):
    out = []
    for t in sorted(doc["strategies"], key=id_key):
        out += ["### " + strategy_title(t), ""]
        out += ["- %s: %s" % (label, cell(t["l3_business"][field])) for field, label in L3_FIELDS]
        out.append("")
    return out[:-1]


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
    """Gaps (blocking ones marked; a draft nests the searches that resolve them), discrepancies with subjects,
    structural changes and open questions."""
    findings = sorted(doc["findings"], key=id_key)
    searches = [] if doc["run"]["status"] == "final" else sorted(doc["next_searches"], key=id_key)
    gaps = []
    for f in findings:
        if f["type"] != "gap":
            continue
        gaps.append(finding_line(f, marker="[BLOCKING] " if f["blocking"] else ""))
        if f["blocking"]:
            gaps += ["  " + search_line(n) for n in searches if f["id"] in n["resolves"]]
    out = ["### Gaps", ""] + (gaps or [NONE])
    out += ["", "### Discrepancies", ""]
    out += [finding_line(f, subjects=True) for f in findings if f["type"] == "discrepancy"] or [NONE]
    out += ["", "### Structural changes", ""]
    out += [finding_line(f) for f in findings if f["type"] == "structural_change"] or [NONE]
    out += ["", "### Open questions", ""]
    out += ["- [%s] %s" % (q["topic"], md_text(q["question"], 200)) for q in doc["open_questions"]] or [NONE]
    return out


def _requests(doc):
    return [request_line(q) for q in sorted(doc["issuer_requests"], key=id_key)]


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
    return out[:-1]


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
    "- CONFIRMED: verified by an independent source (legal facts: regulator, registry, auditor or on-chain).",
    "- PARTIALLY_VERIFIED: self-reported by the project or the subject, or inferred from the cited evidence.",
    "- UNRESOLVED: not found in the cited sources, or not searched when no source is cited.",
    "- CONFLICTING: named by a discrepancy finding (see section 13).",
    "- Layers: L1 on-chain capital vault; L2 credit financing layer; L3 underlying business layer.",
    "- Route (L1->L2): POOL supply to a shared lending pool; FUND subscription to a fund or vehicle; DIRECT financing"
    " of the credit counterparty itself; WRAPPER a position in another vault or token that holds the exposure.",
    "- Method (L2->L3): DL direct loan; DI debt instrument (note, bond); AP purchase of receivables or other"
    " assets; PI participation interest; REPO repurchase agreement; PT principal purchase and resale (trade"
    " finance).",
    "- Legal class: DL loan claim; DI debt instrument claim; AP ownership of purchased assets; PI participation"
    " interest; FI fund interest; EI equity interest; OTHER other or contractual claim.",
    "- Flow views: settlement (capital and asset movement); claim (legal rights and collateral);"
    " repayment (cash back to L2 and L1, fees, enforcement path).",
    "- Lanes: offchain, boundary (conversion, bridge and custody hand-off points), onchain.",
    "- Diagram suffixes: [C] CONFIRMED, [P] PARTIALLY_VERIFIED, [U] UNRESOLVED ([U?] not searched),"
    " [X] CONFLICTING.",
    "- Findings: G gap, D discrepancy, C structural change; issuer requests Q cite the research question codes"
    " they answer. No risk scores are given.",
]


def render(doc, rounds=(), figures=None, rejected=()):
    """Render a structurally valid document; rounds = [(heading, text), ...];
    figures = {"T<n>-<view>": SVG text}: a figure gets an image link to <slug>.flow-T<n>-<view>.svg;
    rejected = N ids the analyst rejected, marked in Appendix D (final reports only)."""
    figures = figures or {}
    cell = _Cells(doc)
    name = doc["project"]["name"]["value"]
    title = doc["run"]["slug"] if name is None else fmt_value(name)
    lines = ["# RWA Due Diligence: " + title, ""]
    lines += _metadata(doc, rounds)
    if doc["run"]["status"] == "draft":
        lines += ["", "> DRAFT -- not finalized"]

    sections = (
        ("1. Executive summary", [md_text(doc["narrative"]["executive_summary"], 800)]
         if doc["narrative"]["executive_summary"] else []),
        ("2. Framework completeness", _completeness(doc)),
        ("3. Three-layer functional map", _functional_map(doc, cell)),
        ("4. Legal entity register", _register(doc, cell)),
        ("5. L1 -> L2 capital allocation", _l1_l2(doc, cell)),
        ("6. L2 -> L3 underlying transactions", _l2_l3(doc, cell)),
        ("7. Holder legal rights", _holder_rights(doc, cell)),
        ("8. Default and recovery path", _default_path(doc, cell)),
        ("9. L3 business", _l3_business(doc, cell)),
        ("10. Yield, fees and redemption", _yield(doc, cell)),
        ("11. Fund flows", _flows(doc, figures, cell)),
        ("12. On-chain contracts and control", _onchain(doc, cell)),
        ("13. Findings", _findings(doc)),
        ("14. Issuer requests", _requests(doc)),
        ("15. Audits and size", _audits_size(doc, cell)),
        ("16. History", _history(doc)),
        ("17. Sources", _sources(doc)),
        ("Appendix A. Analyst interventions", _interventions(rounds)),
        ("Appendix B. Unmapped facts", _unmapped(doc)),
        ("Appendix C. Legend", LEGEND),
    )
    if doc["run"]["status"] == "final":
        sections += (("Appendix D. Searches not run", _not_run(doc, rejected)),)
    for heading, body in sections:
        lines += ["", "## " + heading, ""]
        lines += body or [NONE]
    return "\n".join(lines).rstrip("\n") + "\n"
