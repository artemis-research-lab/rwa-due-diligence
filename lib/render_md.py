"""Markdown report renderer (section 3.8); deterministic, adds only fixed headings, labels and the legend."""

import json

from lib import schema
from lib.textutil import finding_line, id_key, md_text, search_line

MARKERS = {"verified": "V", "self_reported": "S", "inferred": "I", "not_found": "N"}
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


def claim_cell(claim):
    """`<value> [V|S|I|N] (S1, S4) -- note`; `[N?]` marks not_found without evidence (not searched)."""
    marker = MARKERS[claim["status"]]
    if claim["status"] == "not_found" and not claim["evidence"]:
        marker = "N?"
    cell = "%s [%s]" % (fmt_value(claim["value"]), marker)
    if claim["evidence"]:
        cell += " (%s)" % ", ".join(claim["evidence"])
    if claim["note"]:
        cell += " -- " + md_text(claim["note"], schema.CLAIM_NOTE_MAX)
    return cell


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


# --------------------------------------------------------------------------- sections

def _metadata(doc):
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
    return table(("field", "value"), [list(r) for r in rows])


def _blocking(doc):
    searches = sorted(doc["next_searches"], key=id_key)
    out = []
    for f in sorted(doc["findings"], key=id_key):
        if f["type"] == "gap" and f["blocking"]:
            out.append(finding_line(f))
            out += ["  " + search_line(n) for n in searches if f["id"] in n["resolves"]]
    return out


def _products(doc):
    project = doc["project"]
    out = ["- Project name: " + claim_cell(project["name"]),
           "- Asset class: " + claim_cell(project["asset_class"]), ""]
    rows = [[p["id"], claim_cell(p["name"]), claim_cell(p["symbol"]), claim_cell(p["chains"]),
             claim_cell(p["token_addresses"]), claim_cell(p["asset_class"])]
            for p in sorted(project["products"], key=id_key)]
    return out + table(("id", "name", "symbol", "chains", "token addresses", "asset class"), rows)


def _legal(doc):
    entities = sorted(doc["entities"], key=id_key)
    out = ["### Entities", ""]
    out += table(("id", "legal name", "jurisdiction", "entity type", "registration id", "roles", "license status"),
                 [[e["id"], claim_cell(e["legal_name"]), claim_cell(e["jurisdiction"]),
                   claim_cell(e["entity_type"]), claim_cell(e["registration_id"]), "; ".join(e["roles"]),
                   claim_cell(e["license_status"])] for e in entities])
    licenses = [[e["id"], claim_cell(lic["regulator"]), claim_cell(lic["license_type"]),
                 claim_cell(lic["license_id"]), claim_cell(lic["status"])]
                for e in entities for lic in e["licenses"]]
    if licenses:
        out += [""] + table(("entity", "regulator", "license type", "license id", "license status"), licenses)
    out += ["", "### Relationships", ""]
    out += table(("from", "to", "type", "claim"),
                 [[r["from"], r["to"], r["type"], claim_cell(r["claim"])] for r in doc["relationships"]])
    out += ["", "### Governing law", "", claim_cell(doc["governing_law"])]
    return out


def _yield(doc):
    out = []
    for p in sorted(doc["project"]["products"], key=id_key):
        out += ["### " + product_title(p), ""]
        entries = [y for y in doc["yield"] if y["product"] == p["id"]]
        if not entries:
            out += [NONE, ""]
        for y in entries:
            out += [
                "- Mechanism: " + claim_cell(y["mechanism"]),
                "- Gross yield: " + claim_cell(y["gross_yield"]),
                "- Net yield to holder: " + claim_cell(y["net_yield_to_holder"]),
                "- Distribution method: " + claim_cell(y["distribution"]["method"]),
                "- Distribution frequency: " + claim_cell(y["distribution"]["frequency"]),
                "- Loss absorption: " + claim_cell(y["loss_absorption"]),
                "",
                "Underlying:",
                "",
            ]
            out += table(("description", "asset class", "share pct", "location"),
                         [[claim_cell(u["description"]), claim_cell(u["asset_class"]),
                           claim_cell(u["share_pct"]), claim_cell(u["location"])] for u in y["underlying"]])
            out += ["", "Fees:", ""]
            out += table(("type", "rate", "recipient"),
                         [[claim_cell(f["type"]), claim_cell(f["rate"]), claim_cell(f["recipient"])]
                          for f in y["fees"]])
            out.append("")
    return out[:-1] if out and out[-1] == "" else out


def _flows(doc, figures):
    nodes = {n["id"]: n for n in doc["flows"]["nodes"]}

    def node_cell(nid):
        node = nodes.get(nid)
        return nid if node is None else "%s %s" % (nid, md_text(node["label"], 40))

    out = ["Nodes:", ""]
    out += table(("id", "label", "lane", "kind", "chain", "ref"),
                 [[n["id"], md_text(n["label"], 40), n["lane"], n["kind"], text(n["chain"], 24), text(n["ref"])]
                  for n in sorted(doc["flows"]["nodes"], key=id_key)])
    for p in sorted(doc["project"]["products"], key=id_key):
        out += ["", "### " + product_title(p), ""]
        if p["id"] in figures:
            out += ["![Fund flow %s](%s.flow-%s.svg)" % (p["id"], doc["run"]["slug"], p["id"]), ""]
        out += table(("from", "to", "kind", "mechanism", "rail", "label", "claim"),
                     [[node_cell(e["from"]), node_cell(e["to"]), e["kind"], e["mechanism"], e["rail"],
                       md_text(e["label"], 40), claim_cell(e["claim"])]
                      for e in doc["flows"]["edges"] if p["id"] in e["products"]])
    return out


def _onchain(doc):
    rows = []
    for c in doc["onchain"]["contracts"]:
        ctl = c["control"]
        ms = ctl["multisig"]
        rows.append([text(c["chain"], 24), text(c["address"], 64), claim_cell(c["role"]),
                     claim_cell(c["source_verified"]), claim_cell(c["proxy"]), claim_cell(ctl["upgrade_admin"]),
                     claim_cell(ctl["role_admins"]), claim_cell(ctl["timelock_delay_s"]),
                     claim_cell(ms["address"]), claim_cell(ms["threshold"]), claim_cell(ms["signers_count"])])
    return table(("chain", "address", "role", "source verified", "proxy", "upgrade admin", "role admins",
                  "timelock delay s", "multisig", "threshold", "signers"), rows)


def _redemption(doc):
    out = ["Redemption:", ""]
    out += table(("product", "mechanism", "queue", "settlement time", "gating", "fees"),
                 [[r["product"], claim_cell(r["mechanism"]), claim_cell(r["queue"]),
                   claim_cell(r["settlement_time"]), claim_cell(r["gating"]), claim_cell(r["fees"])]
                  for r in sorted(doc["redemption"], key=lambda r: id_key(r["product"]))])
    out += ["", "Eligibility:", ""]
    out += table(("product", "restrictions"),
                 [[e["product"], claim_cell(e["restrictions"])]
                  for e in sorted(doc["eligibility"], key=lambda e: id_key(e["product"]))])
    return out


def _audits(doc):
    return table(("auditor", "scope", "date", "report"),
                 [[claim_cell(a["auditor"]), claim_cell(a["scope"]), claim_cell(a["date"]), text(a["report_ref"])]
                  for a in doc["audits"]])


def _size(doc):
    return table(("product", "metric", "value", "as of"),
                 [[text(s["product"]), s["metric"], claim_cell(s["value"]), text(s["as_of"])] for s in doc["size"]])


def _history(doc):
    return table(("date", "change", "evidence"),
                 [[text(h["date"]), md_text(h["change"], 200), ", ".join(h["evidence"])] for h in doc["history"]])


def _findings(doc):
    findings = sorted(doc["findings"], key=id_key)
    out = []
    for title, pred in (("Discrepancies", lambda f: f["type"] == "discrepancy"),
                        ("Structural changes", lambda f: f["type"] == "structural_change"),
                        ("Other gaps", lambda f: f["type"] == "gap" and not f["blocking"])):
        out += ["### " + title, ""]
        out += [finding_line(f) for f in findings if pred(f)] or [NONE]
        out.append("")
    return out[:-1]


def _questions(doc):
    return ["- [%s] %s" % (q["topic"], md_text(q["question"], 200)) for q in doc["open_questions"]]


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
    for round_no, body in rounds:
        body = body.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
        fence = _fence(body)
        out += ["### Round %d" % round_no, "", fence + "text"] + body.split("\n") + [fence, ""]
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
    "- Claim cell: `value [marker] (evidence) -- note`.",
    "- V verified: supported by an independent source (legal facts: regulator, registry, auditor or on-chain).",
    "- S self_reported: supported only by the project or the subject itself.",
    "- I inferred: derived by the analyst from the cited evidence; the note explains how.",
    "- N not_found: checked in the cited sources and absent.",
    "- N? not_found without evidence: not searched.",
    "- `--`: no value.",
    "- Lanes: offchain, boundary (conversion, bridge and custody hand-off points), onchain.",
    "- Findings: G gap, D discrepancy, C structural change. No risk scores are given.",
]


def render(doc, rounds=(), figures=None):
    """Render a structurally valid document; rounds = [(k, directives.txt text), ...];
    figures = {product id: SVG text}: a product with a figure gets an image link to <slug>.flow-<id>.svg."""
    figures = figures or {}
    name = doc["project"]["name"]["value"]
    title = doc["run"]["slug"] if name is None else fmt_value(name)
    lines = ["# RWA Due Diligence: " + title, ""]
    lines += _metadata(doc)
    if doc["run"]["status"] == "draft":
        lines += ["", "> DRAFT -- not finalized"]

    sections = (
        ("1. Executive summary", [md_text(doc["narrative"]["executive_summary"], 800)]
         if doc["narrative"]["executive_summary"] else []),
        ("2. Blocking gaps and materials to request", _blocking(doc)),
        ("3. Products", _products(doc)),
        ("4. Legal structure", _legal(doc)),
        ("5. Yield source", _yield(doc)),
        ("6. Fund flows", _flows(doc, figures)),
        ("7. On-chain contracts and control", _onchain(doc)),
        ("8. Redemption and eligibility", _redemption(doc)),
        ("9. Audits", _audits(doc)),
        ("10. Size", _size(doc)),
        ("11. History", _history(doc)),
        ("12. Findings", _findings(doc)),
        ("13. Open questions", _questions(doc)),
        ("14. Sources", _sources(doc)),
        ("Appendix A. Analyst interventions", _interventions(rounds)),
        ("Appendix B. Unmapped facts", _unmapped(doc)),
        ("Appendix C. Legend", LEGEND),
    )
    for heading, body in sections:
        lines += ["", "## " + heading, ""]
        lines += body or [NONE]
    return "\n".join(lines).rstrip("\n") + "\n"
