"""Markdown report renderer (section 3.8, v0.6.0 section 6, v0.7.0 section 5.2: six reader sections, detail in
appendices A-O) and the derived data file (v0.7.0 7.3, v0.7.2 sections 1 and 2); deterministic, adds only fixed
headings, labels and the legend."""

import json
import re

from lib import claims, flow, framework, qa, review, schema
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


def _sources(claim, basis=()):
    """`(S1, S2)`, `(S1; origin issuer_management; assurance NOT_TESTED)`, `(S2, S4; origin registry; basis S2)`;
    empty without any of them. basis is the verification basis of a verified claim (v0.7.4 section 3)."""
    parts = [", ".join(claim["evidence"])] if claim["evidence"] else []
    if claim["origin"] is not None:
        parts.append("origin " + claim["origin"])
    if claim["assurance"] is not None:
        parts.append("assurance " + claim["assurance"])
    if basis:
        parts.append("basis " + ", ".join(basis))
    return " (%s)" % "; ".join(parts) if parts else ""


def _tail(claim, flag, basis=()):
    cell = "[%s]%s" % (flag, _sources(claim, basis))
    if claim["note"]:
        cell += " -- " + md_text(claim["note"], schema.CLAIM_NOTE_MAX)
    return cell


def claim_cell(claim, flag=None, basis=()):
    """`<value> [FLAG] (S1, S4; basis S4) -- note`; flag defaults to the one derived from the status alone."""
    flag = framework.flag(claim, False) if flag is None else flag
    return "%s %s" % (fmt_value(claim["value"]), _tail(claim, flag, basis))


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


def amount_cell(amount, flag=None, basis=()):
    """`<value> <unit> <BASIS> data <as_of or not established> (<time basis>) [FLAG] (sources)` for one amount
    entry (v0.7.2 section 2)."""
    claim = amount["value"]
    flag = framework.flag(claim, False) if flag is None else flag
    data = "not established" if amount["as_of"] is None else md_text(amount["as_of"])
    return "%s %s %s data %s (%s) [%s]%s" % (fmt_value(claim["value"]), md_text(amount["unit"], 20),
                                             amount["basis"], data, framework.time_basis(amount), flag,
                                             _sources(claim, basis))


def _amount_scopes(interfaces):
    """`Amount scopes` list after a table with amounts: `- X2[0]: <scope>`."""
    lines = ["- %s[%d]: %s" % (x["id"], j, md_text(a["scope"], 200)) for x in interfaces
             for j, a in enumerate(x["amounts"])]
    return ["", "Amount scopes:", ""] + lines if lines else []


class _Cells:
    """claim_cell with the document's derived flags (conflicts included) and verification bases."""

    def __init__(self, doc):
        by_parts = framework.flags(doc)
        sources_by_id = {s["id"]: s for s in doc["sources"]}
        self.by_id = {}
        self.basis_by_id = {}
        for parts, claim in schema.iter_claims(doc):
            self.by_id[id(claim)] = by_parts[parts]
            if claim["status"] == "verified":
                self.basis_by_id[id(claim)] = claims.verification_basis(parts, claim, sources_by_id)

    def flag(self, claim):
        return self.by_id.get(id(claim))

    def basis(self, claim):
        return self.basis_by_id.get(id(claim), ())

    def __call__(self, claim):
        return claim_cell(claim, self.flag(claim), self.basis(claim))

    def amounts(self, x):
        return "; ".join(amount_cell(a, self.flag(a["value"]), self.basis(a["value"]))
                         for a in x["amounts"]) or "--"

    def supply(self, x):
        """`ratio [FLAG] (numerator / denominator @as_of, block, chain) (sources) -- note`."""
        sc = x["supply_concentration"]
        ratio = sc["ratio"]
        cell = "%s [%s]" % (fmt_value(ratio["value"]), self.flag(ratio))
        if ratio["value"] is not None or sc["numerator"] or sc["as_of"] is not None:
            cell += " (%s / %s @%s, %s, %s)" % (md_text(sc["numerator"] or "n/d", 160),
                                                md_text(sc["denominator"] or "n/d", 160), text(sc["as_of"]),
                                                "--" if sc["block"] is None else str(sc["block"]), text(sc["chain"]))
        cell += _sources(ratio, self.basis(ratio))
        if ratio["note"]:
            cell += " -- " + md_text(ratio["note"], schema.CLAIM_NOTE_MAX)
        return cell


def _alt(x):
    tag = framework.alt_tag(x)
    return "--" if tag is None else tag


# --------------------------------------------------------------------------- metadata

def _span(times):
    """`<earliest> to <latest>`, one value when equal, `n/d` without any."""
    times = sorted(t for t in times if t is not None)
    if not times:
        return "n/d"
    return times[0] if times[0] == times[-1] else "%s to %s" % (times[0], times[-1])


def _data_as_of(doc):
    """Earliest and latest amount data time (as_of)."""
    return _span(a["as_of"] for x in doc["interfaces"] for a in x["amounts"])


def _sources_retrieved(doc):
    """Earliest and latest retrieved_at among the sources cited by amount values."""
    cited = {sid for x in doc["interfaces"] for a in x["amounts"] for sid in a["value"]["evidence"]}
    return _span(s["retrieved_at"] for s in doc["sources"] if s["id"] in cited)


def _metadata(doc, rounds=(), today=None):
    run = doc["run"]
    if run["finalized_at"] is not None:
        generated = text(run["finalized_at"])
    else:
        generated = "draft" if today is None else "draft %s" % text(today)
    rows = [
        ("slug", text(run["slug"])),
        ("root URL", text(run["root_url"], 500)),
        ("run id", text(run["run_id"])),
        ("status", run["status"]),
        ("rounds", str(run["round"])),
        ("started", text(run["started_at"])),
        ("finalized", text(run["finalized_at"])),
        ("Report generated", generated),
        ("Data as of", _data_as_of(doc)),
        ("Sources retrieved", _sources_retrieved(doc)),
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

CREDIT_COMPONENTS = ("CORE_CREDIT", "DEFI_LENDING")


def _tags(f):
    tags = (["[MATERIAL]"] if f["material"] else []) + (["[BLOCKING]"] if f["blocking"] else [])
    if f["k_checks"]:
        tags.append("[%s]" % ", ".join(f["k_checks"]))
    if f["impact"]:
        tags.append("[%s]" % ", ".join(f["impact"]))
    return tags


def critical_line(f):
    """`- [MATERIAL] [BLOCKING] [K1, K3] [capital_control] **G1** (CONFLICTING) statement (S8)`."""
    parts = _tags(f) + ["**%s**" % f["id"]]
    status = framework.conflict_status(f)
    if status is not None:
        parts.append("(%s)" % status)
    parts.append(md_text(f["statement"], 280))
    line = "- " + " ".join(parts)
    if f["evidence"]:
        line += " (%s)" % ", ".join(f["evidence"])
    return line


def _critical(doc):
    findings = {f["id"]: f for f in doc["findings"]}
    selected, _, rest = framework.critical_counts(doc)
    out = [critical_line(findings[ident]) for ident in framework.critical(doc)] or [NONE]
    return out + ["", "%d critical findings shown (target 5-8; all material items are always shown). %d further "
                      "open findings in section 6." % (selected, rest)]


def credit_strategies(doc):
    return [t for t in sorted(doc["strategies"], key=id_key) if t["component"] in CREDIT_COMPONENTS]


def _executive(doc):
    out = []
    if doc["narrative"]["executive_summary"]:
        out += [md_text(doc["narrative"]["executive_summary"], 800), ""]
    for t in credit_strategies(doc):
        out += ["### " + strategy_title(t), ""]
        out += table(("question", "answer"), [[q, md_text(a)] for q, a in framework.five_questions(doc, t["id"])])
        out.append("")
    out += ["### Critical findings", ""]
    return out + _critical(doc)


# --------------------------------------------------------------------------- 2. completeness and portfolio

def _completeness(doc):
    names = {t["id"]: t for t in doc["strategies"]}
    return table(["strategy"] + ["%s %s" % (code, label) for code, label in framework.CHECKS],
                 [[strategy_title(names[sid])] + [fl for _, _, fl in checks]
                  for sid, checks in framework.completeness(doc)])


def _totals_rows(totals):
    rows = []
    for scope, label in (("strategies", "strategy"), ("components", "component"), ("products", "product")):
        for name, entries in totals[scope].items():
            rows.append([label, name, totals_text(entries)])
    return rows


def _portfolio(doc, cell):
    totals = framework.allocation_totals(doc)
    out = ["### Completeness", ""] + _completeness(doc)
    out += ["", "### Portfolio components", ""]
    out += table(("strategy", "component", "deployment", "products", "business type", "counted totals"),
                 [[strategy_title(t), t["component"], cell(t["deployment"]),
                   ", ".join(sorted(t["products"], key=id_key)), cell(t["business_type"]),
                   totals_text(totals["strategies"].get(t["id"], []))]
                  for t in sorted(doc["strategies"], key=id_key)])
    out += ["", "### Allocation", ""]
    out += review.amounts_table(doc) or [NONE]
    out += ["", "### Totals by strategy, component and product", ""]
    out += table(("level", "name", "counted totals"), _totals_rows(totals))
    return out + ["", "Totals add only amounts with the same basis, unit and data date; see Appendix N for the"
                      " checks."]


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
    l1 = _interfaces(doc, ("holder_L1", "L1_L2", "within_L1"))
    out = ["### L1 -> L2", ""]
    out += table(("id", "strategy", "from -> to", "route", "legal class", "counterparty", "instrument",
                  "claim holder", "amounts", "supply concentration", "alternative", "terms", "governing law"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["route"]), cell(x["legal_class"]),
                   cell(x["counterparty"]), cell(x["instrument"]), cell(x["claim_holder"]), cell.amounts(x),
                   cell.supply(x), _alt(x), cell(x["terms"]), cell(x["governing_law"])] for x in l1])
    out += _amount_scopes(l1)
    l2 = _interfaces(doc, ("L2_L3", "within_L2", "within_L3", "L3_L3O"))
    out += ["", "### L2 -> L3", ""]
    out += table(("id", "strategy", "from -> to", "method", "legal class", "counterparty", "security",
                  "collateral", "perfection", "enforcement", "recourse", "amounts", "alternative", "terms"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["method"]), cell(x["legal_class"]),
                   cell(x["counterparty"]), cell(x["security"]), cell(x["collateral"]), cell(x["perfection"]),
                   cell(x["enforcement"]), cell(x["recourse"]), cell.amounts(x), _alt(x), cell(x["terms"])]
                  for x in l2])
    out += _amount_scopes(l2)
    sleeves = _interfaces(doc, ("sleeve_holding", "reserve_lookthrough"))
    out += ["", "### Liquidity sleeves", ""]
    out += table(("id", "strategy", "from -> to", "legal class", "instrument", "amounts", "terms"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["legal_class"]), cell(x["instrument"]),
                   cell.amounts(x), cell(x["terms"])] for x in sleeves])
    out += _amount_scopes(sleeves)
    sales = _interfaces(doc, ("asset_sale",))
    out += ["", "### Asset sales", ""]
    out += table(("id", "strategy", "from -> to", "loan identity", "seller of record", "buyer of record",
                  "legal transfer (title_transfer)", "repayment source", "servicer after exit (servicing)",
                  "recourse", "retained exposure (residual_exposure)", "amounts"),
                 [[x["id"], x["strategy"], md_text(_ends(x)), cell(x["loan_identity"]), cell(x["seller_of_record"]),
                   cell(x["buyer_of_record"]), cell(x["title_transfer"]), cell(x["repayment_source"]),
                   cell(x["servicing"]), cell(x["recourse"]), cell(x["residual_exposure"]), cell.amounts(x)]
                  for x in sales])
    return out + _amount_scopes(sales)


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
        return [label + _tail(claim, cell.flag(claim), cell.basis(claim))] + [
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

def finding_detail(f):
    """A finding with its scope note, scope match, assertions, subjects and resolution (section 6)."""
    out = [finding_line(f)]
    if f["scope_note"]:
        out.append("  - scope: " + md_text(f["scope_note"], 200))
    out.append("  - scope match: " + f["scope_match"])
    out += ["  - assertion %s (%s): %s" % (a["source"], text(a["as_of"]), md_text(a["statement"], 200))
            for a in f["assertions"]]
    if f["subjects"]:
        out.append("  - subjects: " + ", ".join(md_text(s) for s in f["subjects"]))
    resolution = f["resolution"]
    out.append("  - resolution: %s%s" % (resolution["status"],
                                         " -- " + md_text(resolution["note"], 200) if resolution["note"] else ""))
    return out


SECTION6_GROUPS = (
    ("Material", lambda f: f["material"]),
    ("Blocking", lambda f: f["blocking"]),
    ("Conflicts", lambda f: f["type"] == "discrepancy" and framework.conflict_status(f) is not None),
    ("Scope unresolved", lambda f: f["type"] == "scope_unresolved"),
    ("Unreconciled transactions", lambda f: f["type"] == "unreconciled_transaction"),
    ("Other gaps", lambda f: f["type"] == "gap"),
)


def _gaps_requests(doc):
    shown = set(framework.critical(doc))
    pending = [f for f in sorted(doc["findings"], key=id_key)
               if f["id"] not in shown and f["resolution"]["status"] == "open"]
    out = []
    for heading, pred in SECTION6_GROUPS:
        group = [f for f in pending if pred(f)]
        pending = [f for f in pending if not pred(f)]
        out += ["### " + heading, ""]
        out += [line for f in group for line in finding_detail(f)] or [NONE]
        out.append("")
    out += ["### Issuer requests", ""]
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
    register = table(("id", "type", "scope match", "resolution", "k_checks", "impact", "priority", "carried from"),
                     [[f["id"], f["type"], f["scope_match"], f["resolution"]["status"],
                       ", ".join(f["k_checks"]) or "--", ", ".join(f["impact"]) or "--", str(f["priority"]),
                       text(f["carried_from"])] for f in findings])
    gaps = []
    for f in findings:
        if f["type"] != "gap":
            continue
        marker = ("[MATERIAL] " if f["material"] else "") + ("[BLOCKING] " if f["blocking"] else "")
        gaps.append(finding_line(f, marker=marker))
        if f["blocking"]:
            gaps += ["  " + search_line(n) for n in searches if f["id"] in n["resolves"]]
    out = ["### Finding register", ""] + register
    out += ["", "### Gaps", ""] + (gaps or [NONE])
    out += ["", "### Discrepancies", ""]
    out += [finding_line(f, subjects=True, scope=True) for f in findings if f["type"] == "discrepancy"] or [NONE]
    out += ["", "### Scope unresolved", ""]
    out += [finding_line(f, subjects=True, scope=True) for f in findings if f["type"] == "scope_unresolved"] or [NONE]
    out += ["", "### Unreconciled transactions", ""]
    out += [finding_line(f, subjects=True, scope=True) for f in findings
            if f["type"] == "unreconciled_transaction"] or [NONE]
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


URL_HOST = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://(?:[^/?#@]*@)?([^/?#:]+)")


def publication(source):
    """`<host> (<source_type>)`: where a source was published (curator AC-05); `--` for a URL without a host."""
    match = URL_HOST.match(source["url"])
    host = match.group(1).lower() if match else None
    return "%s (%s)" % (md_text(host) if host else "--", source["source_type"])


def _correction_line(c):
    changed = "; ".join("%s %s -> %s" % (md_text(key), text(c["previous"][key]), text(c["fields"][key]))
                        for key in sorted(c["fields"]))
    return "- %s: %s (corrected %s) -- %s" % (c["correction"], changed, text(c["corrected_at"]),
                                              md_text(c["reason"], schema.CORRECTION_REASON_MAX))


def _sources_table(doc, corrections=()):
    rows = []
    for s in sorted(doc["sources"], key=id_key):
        fetch = s["fetch"]
        if s["archived"]:
            if fetch != "archived":
                fetch += ", archived"
            fetch += " (version %s)" % text(s["version_date"])
        rows.append([s["id"], s["source_type"], s["origin"], "publication: " + publication(s), fetch,
                     text(s["retrieved_at"]), "%s -- %s" % (md_text(s["title"], 200), md_text(s["url"], 500)),
                     md_text(s["note"], 200)])
    out = table(("id", "type", "origin", "publication", "fetch", "retrieved", "title/url", "note"), rows)
    if corrections:
        out += ["", "Ledger corrections (append-only; previous -> revised):", ""]
        out += [_correction_line(c) for c in corrections]
    return out


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
    " regulator, registry, auditor or on-chain sources only). The cell names its verification basis (`basis"
    " S<n>`): a regulator record, registry entry, on-chain read, tested auditor procedure, or for non-legal facts"
    " an independent third party; a filer's disclosure is never one (curator AC-05).",
    "- Attribution (curator AC-05): a company filing (10-K, 10-Q, 8-K, prospectus, exhibit) has origin filer"
    " (first_party when the filer is the project): the regulator only hosts it; origin regulator is limited to"
    " records the regulator issues or keeps. Appendix I shows where each source was published"
    " (`publication: <host> (<type>)`) and every append-only ledger correction. Enforcement, perfection,"
    " enforceability and insolvency protection are never CONFIRMED or INFERRED from disclosures alone.",
    "- SELF_REPORTED: stated by the issuer, protocol, borrower or another interested party.",
    "- THIRD_PARTY_REPORTED: reported by a third party; its scope and authority still need assessing.",
    "- INFERRED: the analyst's conclusion from cited facts; the note states the reasoning.",
    "- UNRESOLVED: not found in the cited sources, or not searched when no source is cited.",
    "- CONFLICTING: named by an open discrepancy finding whose scope was matched (same fact, timeframe and scope,"
    " with two recorded assertions; see Appendix F); scope-unresolved findings, unreconciled transactions and"
    " resolved discrepancies never make a claim CONFLICTING.",
    "- Conflict statuses of findings: CONFLICTING (open matched discrepancy), RESOLVED (resolved discrepancy),"
    " SCOPE_UNRESOLVED (statements may cover different scopes), UNRECONCILED_TRANSACTION (accounts of one"
    " transaction not reconciled).",
    "- Provenance (curator Q8): origin is who asserted the fact (issuer_management, issuer_documents, borrower,"
    " regulator, registry, onchain, independent_party, auditor_procedure, analyst); the cited sources are where"
    " it was published; assurance is what an auditor or reviewer tested for this precise claim (TESTED,"
    " NOT_TESTED, NOT_APPLICABLE). An issuer statement quoted in an auditor's publication stays SELF_REPORTED with"
    " assurance NOT_TESTED; a claim is CONFIRMED through an auditor only with origin auditor_procedure and"
    " assurance TESTED; a regulator, registry or on-chain verification keeps its origin, and assurance states"
    " whether a cited auditor also tested it.",
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
    "- Amount cell: `<value> <unit> <BASIS> data <data as of> (<time basis>) [FLAG] (sources)`. Data as of is the"
    " time the value applies as the source establishes it (statement or report date, API updatedAt, block time),"
    " `not established` when the source gives none; it is never the time a page was opened or the report date."
    " Time basis: block (on-chain read at a block, data as of is the block timestamp), source (date given by the"
    " source), unresolved (no data time; shown, not counted). Observed at is the latest retrieval time of the"
    " cited sources (Appendix I), metadata only, never a data time (curator AC-03). Bases:",
] + ["  - %s: %s." % (name, meaning) for name, meaning in schema.AMOUNT_BASIS_MEANINGS] + [
    "- Counting rule: only CURRENT_BALANCE, POSITION_VALUE and OUTSTANDING_PRINCIPAL amounts on L1_L2 and"
    " sleeve_holding interfaces, with a data time established by the source or the block, outside alternative"
    " groups and not migration placeholders, are counted; totals add only amounts with the same basis, unit,"
    " valuation basis and data date (label `<sum> <unit> <BASIS> @<date>`); everything else is linked, not"
    " summed.",
    "- Deployment of a credit strategy: DEPLOYED_VERIFIED (transfers into the credit arrangement verified),"
    " DISCLOSED_UNVERIFIED (path disclosed, settlement not shown), NOT_DEPLOYED, UNRESOLVED.",
    "- Alternative tag: `alt A1a` marks option a of alternative group A1, competing legal paths for one position;"
    " they are never parallel exposures and are not counted.",
    "- Flow views: settlement (capital and asset movement); claim (legal rights and collateral);"
    " repayment (cash back to L2 and L1, fees, enforcement path).",
    "- Lanes: offchain, boundary (conversion, bridge and custody hand-off points), onchain.",
    "- Diagram suffixes: [C] CONFIRMED, [S] SELF_REPORTED, [T] THIRD_PARTY_REPORTED, [I] INFERRED,"
    " [U] UNRESOLVED ([U?] not searched), [X] CONFLICTING.",
    "- Findings: G gap, D discrepancy, U scope unresolved, R unreconciled transaction, C structural change; issuer"
    " requests Q cite the research question codes they answer. No risk scores are given.",
]


def _checks(results):
    out = table(("id", "rule", "result", "target", "mapping", "detail"),
                [[r["id"], md_text(r["rule"], 120), r["result"], text(r["target"]), md_text(r["mapping"]) or "--",
                  md_text(r["detail"])] for r in results])
    return out + ["", "Rules:", ""] + ["- %s %s: %s" % rule for rule in schema.QA_RULES]


def _change_table(rows):
    return table(("ref", "path", "change", "before", "after", "evidence added"),
                 [[md_text(r["ref"]), md_text(r["path"]) or "--", r["change"], text(r["before"]),
                   text(r["after"]), ", ".join(r["evidence_added"]) or "--"] for r in rows])


def _changes(doc, rows, amendment=0, amendment_rows=()):
    out = ["No earlier run."] if doc["run"]["seeded_from"] is None else _change_table(rows)
    if amendment >= 1:
        out += ["", "### Changes in amendment %d" % amendment, ""] + _change_table(amendment_rows)
    return out


def render(doc, rounds=(), figures=None, rejected=(), qa_results=None, change_rows=None, today=None,
           corrections=(), amendment=0, amendment_rows=()):
    """Render a structurally valid document; rounds = [(heading, text), ...];
    figures = {"T<n>-<view>": SVG text}: a figure gets an image link to <slug>.flow-T<n>-<view>.svg;
    rejected = N ids the analyst rejected, marked in Appendix M (final reports only);
    qa_results = qa.run output (computed without expectations when None); change_rows = changes.diff rows;
    today = the render clock date shown for a draft in the Report generated row; corrections = ledger correction
    lines (Appendix I); amendment_rows = change rows against the previous final version of amendment
    <amendment> (Appendix O)."""
    figures = figures or {}
    results = qa.run(doc) if qa_results is None else qa_results
    cell = _Cells(doc)
    name = doc["project"]["name"]["value"]
    title = doc["run"]["slug"] if name is None else fmt_value(name)
    lines = ["# RWA Due Diligence: " + title, ""]
    lines += _metadata(doc, rounds, today)
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
        ("Appendix I. Sources", _sources_table(doc, corrections)),
        ("Appendix J. Analyst interventions", _interventions(rounds)),
        ("Appendix K. Unmapped facts", _unmapped(doc)),
        ("Appendix L. Legend", LEGEND),
    )
    if doc["run"]["status"] == "final":
        sections += (("Appendix M. Searches not run", _not_run(doc, rejected)),)
    seeded_from = doc["run"]["seeded_from"]
    sections += (("Appendix N. Quantitative and provenance checks", _checks(results)),
                 ("Appendix O. Changes since %s" % text(seeded_from, 64) if seeded_from else "Appendix O. Changes",
                  _changes(doc, change_rows or [], amendment, amendment_rows)))
    for heading, body in sections:
        while body and body[-1] == "":
            body = body[:-1]
        lines += ["", "## " + heading, ""]
        lines += body or [NONE]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- derived output (v0.7.0 7.3)

DERIVED_VERSION = "rwa-dd-derived/1"


def _sorted_keys(value):
    if isinstance(value, dict):
        return {k: _sorted_keys(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [_sorted_keys(v) for v in value]
    return value


def verification_bases(doc):
    """{claim id: sorted source ids} for every verified claim, sorted by claim id (v0.7.4 section 3)."""
    sources_by_id = {s["id"]: s for s in doc["sources"]}
    return {framework.claim_id(parts, doc): claims.verification_basis(parts, claim, sources_by_id)
            for parts, claim in schema.iter_claims(doc) if claim["status"] == "verified"}


def derived(doc, record_sha256, qa_results, change_rows, amendment_rows=()):
    """The <slug>.derived.json object: flags, conflicts, section 1 selection, allocation, totals, six questions,
    QA results, changes, verification bases and amendment changes, tied to the record by its SHA-256; keys
    sorted."""
    run = doc["run"]
    selected, total, rest = framework.critical_counts(doc)
    conflicts = [{"finding": ident, "conflict_status": status, "scope_match": match, "resolution": resolution,
                  "subjects": subjects, "assertion_sources": sources}
                 for ident, status, match, resolution, subjects, sources in framework.conflicts(doc)]
    return _sorted_keys({
        "derived_version": DERIVED_VERSION, "slug": run["slug"], "run_id": run["run_id"],
        "schema_version": doc["schema_version"], "skill_version": run["skill_version"],
        "record_sha256": record_sha256,
        "flags": framework.flags_by_id(doc),
        "conflicts": conflicts,
        "critical": framework.critical(doc),
        "critical_counts": {"selected": selected, "total": total, "open_not_selected": rest},
        "allocation": [row.as_object() for row in framework.allocation(doc)],
        "totals": framework.allocation_totals(doc),
        "five_questions": {t["id"]: [list(pair) for pair in framework.five_questions(doc, t["id"])]
                           for t in credit_strategies(doc)},
        "qa": list(qa_results),
        "changes": list(change_rows),
        "verification_basis": verification_bases(doc),
        "amendment_changes": list(amendment_rows),
    })
