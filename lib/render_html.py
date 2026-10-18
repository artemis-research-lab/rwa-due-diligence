"""HTML report renderer (D6); mirrors render_md section for section, deterministic, no JavaScript.

Every string from the document passes through textutil.html_text; only http(s) source URLs become links.
"""

import json
from pathlib import Path

from lib import schema
from lib.render_md import LEGEND, MARKERS
from lib.textutil import html_text, html_url, id_key, not_run_suffix

ASSETS = Path(__file__).resolve().parents[1] / "assets"
TEMPLATE = "report.html.tmpl"
LISM_CSS = "lism-css-1.0.1.min.css"
REPORT_CSS = "report.css"

NONE = '<p class="dd-none">none</p>'
BADGES = {"V": ("v", "verified"), "S": ("s", "self_reported"), "I": ("i", "inferred"), "N": ("n", "not_found"),
          "N?": ("nq", "not_found (not searched)")}
LINK_ATTRS = 'rel="noopener noreferrer nofollow" target="_blank"'


# --------------------------------------------------------------------------- cells

def fmt_value(value):
    if value is None:
        return "--"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        return html_text(value, schema.CLAIM_VALUE_STR_MAX)
    if isinstance(value, list):
        return "; ".join(fmt_value(v) for v in value)
    if isinstance(value, dict):
        return "; ".join("%s=%s" % (html_text(k), fmt_value(v)) for k, v in value.items())
    return html_text(str(value))


def text(value, limit=None):
    return "--" if value is None else html_text(value, limit)


def badge(marker):
    suffix, title = BADGES[marker]
    return '<span class="dd-badge dd-badge--%s" title="%s">%s</span>' % (suffix, title, html_text(marker))


class Renderer:
    """Holds the set of source ids so evidence links never dangle."""

    def __init__(self, doc):
        self.doc = doc
        self.source_ids = {s["id"] for s in doc["sources"]}

    def sid(self, ident):
        ident = html_text(ident)
        if ident in self.source_ids:
            return '<a href="#src-%s">%s</a>' % (ident, ident)
        return ident

    def evidence(self, ids):
        return ", ".join(self.sid(i) for i in ids)

    def claim_cell(self, claim):
        marker = MARKERS[claim["status"]]
        if claim["status"] == "not_found" and not claim["evidence"]:
            marker = "N?"
        cell = '<span class="dd-claim">%s %s' % (fmt_value(claim["value"]), badge(marker))
        if claim["evidence"]:
            cell += ' <span class="dd-ev">(%s)</span>' % self.evidence(claim["evidence"])
        if claim["note"]:
            cell += ' <span class="dd-note">-- %s</span>' % html_text(claim["note"], schema.CLAIM_NOTE_MAX)
        return cell + "</span>"

    def finding_item(self, finding, inner=()):
        line = '<li><strong class="dd-id">%s</strong> [%s] %s' % (
            html_text(finding["id"]), html_text(finding["topic"]), html_text(finding["statement"], 280))
        if finding["evidence"]:
            line += " (%s)" % self.evidence(finding["evidence"])
        if inner:
            return [line, '<ul class="dd-list">'] + list(inner) + ["</ul>", "</li>"]
        return [line + "</li>"]


def search_item(search, suffix=""):
    resolves = ", ".join(html_text(r) for r in search["resolves"]) or "none"
    return '<li><strong class="dd-id">%s</strong> %s -- %s -- %s (resolves %s; est %d calls)%s</li>' % (
        html_text(search["id"]), html_text(search["what"], 120), html_text(search["where"], 120),
        html_text(search["why"], 120), resolves, search["est_calls"], html_text(suffix))


def table(header, rows, row_ids=None):
    if not rows:
        return [NONE]
    out = ['<div class="dd-table-wrap">', '<table class="dd-table">', "<thead>",
           "<tr>%s</tr>" % "".join("<th>%s</th>" % html_text(h) for h in header), "</thead>", "<tbody>"]
    for i, row in enumerate(rows):
        attr = ' id="%s"' % row_ids[i] if row_ids else ""
        out.append("<tr%s>%s</tr>" % (attr, "".join("<td>%s</td>" % cell for cell in row)))
    return out + ["</tbody>", "</table>", "</div>"]


def items(lines):
    return ['<ul class="dd-list">'] + ["<li>%s</li>" % line for line in lines] + ["</ul>"]


def h3(title):
    return ["<h3>%s</h3>" % title]


def label(title):
    return ['<p class="dd-label">%s</p>' % title]


def product_title(product):
    name = product["name"]["value"]
    pid = html_text(product["id"])
    return pid if name is None else "%s %s" % (pid, fmt_value(name))


def kind_cell(kind):
    return '<span class="dd-kind dd-kind--%s">%s</span>' % (html_text(kind), html_text(kind))


# --------------------------------------------------------------------------- sections

def _metadata(doc, rounds=()):
    run = doc["run"]
    rows = [
        ("slug", text(run["slug"])),
        ("root URL", text(run["root_url"], 500)),
        ("run id", text(run["run_id"])),
        ("status", html_text(run["status"])),
        ("rounds", str(run["round"])),
        ("started", text(run["started_at"])),
        ("finalized", text(run["finalized_at"])),
        ("skill version", text(run["skill_version"])),
        ("schema version", text(doc["schema_version"])),
    ]
    amendments = sum(1 for heading, _ in rounds if heading.startswith("Amendment "))
    if amendments:
        rows.insert(5, ("amendments", str(amendments)))
    out = ['<dl class="dd-meta">']
    out += ['<div class="dd-meta__row"><dt>%s</dt><dd>%s</dd></div>' % row for row in rows]
    return out + ["</dl>"]


def _blocking(r):
    """Blocking gaps; a draft nests the searches that resolve each gap, a final report lists gaps only."""
    doc = r.doc
    searches = [] if doc["run"]["status"] == "final" else sorted(doc["next_searches"], key=id_key)
    out = []
    for f in sorted(doc["findings"], key=id_key):
        if f["type"] == "gap" and f["blocking"]:
            out += r.finding_item(f, [search_item(n) for n in searches if f["id"] in n["resolves"]])
    return ['<ul class="dd-list">'] + out + ["</ul>"] if out else []


def _not_run(r, rejected):
    lines = [search_item(n, not_run_suffix(n, rejected)) for n in sorted(r.doc["next_searches"], key=id_key)]
    return ['<ul class="dd-list">'] + lines + ["</ul>"] if lines else []


def _products(r):
    project = r.doc["project"]
    cc = r.claim_cell
    out = items(["Project name: " + cc(project["name"]), "Asset class: " + cc(project["asset_class"])])
    rows = [[html_text(p["id"]), cc(p["name"]), cc(p["symbol"]), cc(p["chains"]), cc(p["token_addresses"]),
             cc(p["asset_class"])] for p in sorted(project["products"], key=id_key)]
    return out + table(("id", "name", "symbol", "chains", "token addresses", "asset class"), rows)


def _legal(r):
    doc = r.doc
    cc = r.claim_cell
    entities = sorted(doc["entities"], key=id_key)
    out = h3("Entities")
    out += table(("id", "legal name", "jurisdiction", "entity type", "registration id", "roles", "license status"),
                 [[html_text(e["id"]), cc(e["legal_name"]), cc(e["jurisdiction"]), cc(e["entity_type"]),
                   cc(e["registration_id"]), "; ".join(html_text(x) for x in e["roles"]), cc(e["license_status"])]
                  for e in entities])
    licenses = [[html_text(e["id"]), cc(lic["regulator"]), cc(lic["license_type"]), cc(lic["license_id"]),
                 cc(lic["status"])] for e in entities for lic in e["licenses"]]
    if licenses:
        out += table(("entity", "regulator", "license type", "license id", "license status"), licenses)
    out += h3("Relationships")
    out += table(("from", "to", "type", "claim"),
                 [[html_text(x["from"]), html_text(x["to"]), html_text(x["type"]), cc(x["claim"])]
                  for x in doc["relationships"]])
    out += h3("Governing law") + ["<p>%s</p>" % cc(doc["governing_law"])]
    return out


def _yield(r):
    doc = r.doc
    cc = r.claim_cell
    out = []
    for p in sorted(doc["project"]["products"], key=id_key):
        out += h3(product_title(p))
        entries = [y for y in doc["yield"] if y["product"] == p["id"]]
        if not entries:
            out.append(NONE)
        for y in entries:
            out += items([
                "Mechanism: " + cc(y["mechanism"]),
                "Gross yield: " + cc(y["gross_yield"]),
                "Net yield to holder: " + cc(y["net_yield_to_holder"]),
                "Distribution method: " + cc(y["distribution"]["method"]),
                "Distribution frequency: " + cc(y["distribution"]["frequency"]),
                "Loss absorption: " + cc(y["loss_absorption"]),
            ])
            out += label("Underlying:")
            out += table(("description", "asset class", "share pct", "location"),
                         [[cc(u["description"]), cc(u["asset_class"]), cc(u["share_pct"]), cc(u["location"])]
                          for u in y["underlying"]])
            out += label("Fees:")
            out += table(("type", "rate", "recipient"),
                         [[cc(f["type"]), cc(f["rate"]), cc(f["recipient"])] for f in y["fees"]])
    return out


def _flows(r, figures):
    doc = r.doc
    nodes = {n["id"]: n for n in doc["flows"]["nodes"]}

    def node_cell(nid):
        node = nodes.get(nid)
        return html_text(nid) if node is None else "%s %s" % (html_text(nid), html_text(node["label"], 40))

    out = label("Nodes:")
    out += table(("id", "label", "lane", "kind", "chain", "ref"),
                 [[html_text(n["id"]), html_text(n["label"], 40), html_text(n["lane"]), html_text(n["kind"]),
                   text(n["chain"], 24), text(n["ref"])] for n in sorted(doc["flows"]["nodes"], key=id_key)])
    for p in sorted(doc["project"]["products"], key=id_key):
        out += h3(product_title(p))
        pid = html_text(p["id"])
        if p["id"] in figures:
            # The SVG was sanitized by flow.sanitize_svg; it is the only unescaped content in the page.
            out += ['<figure class="dd-flow" id="flow-%s">' % pid, figures[p["id"]].rstrip("\n"),
                    "<figcaption>Fund flow %s: lanes off-chain / boundary / on-chain; marker after each label"
                    " = claim status</figcaption></figure>" % pid]
        else:
            out.append('<figure class="dd-flow" id="flow-%s"></figure>' % pid)
        out += table(("from", "to", "kind", "mechanism", "rail", "label", "claim"),
                     [[node_cell(e["from"]), node_cell(e["to"]), kind_cell(e["kind"]), html_text(e["mechanism"]),
                       html_text(e["rail"]), html_text(e["label"], 40), r.claim_cell(e["claim"])]
                      for e in doc["flows"]["edges"] if p["id"] in e["products"]])
    return out


def _onchain(r):
    cc = r.claim_cell
    rows = []
    for c in r.doc["onchain"]["contracts"]:
        ctl = c["control"]
        ms = ctl["multisig"]
        rows.append([text(c["chain"], 24), text(c["address"], 64), cc(c["role"]), cc(c["source_verified"]),
                     cc(c["proxy"]), cc(ctl["upgrade_admin"]), cc(ctl["role_admins"]), cc(ctl["timelock_delay_s"]),
                     cc(ms["address"]), cc(ms["threshold"]), cc(ms["signers_count"])])
    return table(("chain", "address", "role", "source verified", "proxy", "upgrade admin", "role admins",
                  "timelock delay s", "multisig", "threshold", "signers"), rows)


def _redemption(r):
    doc = r.doc
    cc = r.claim_cell
    out = label("Redemption:")
    out += table(("product", "mechanism", "queue", "settlement time", "gating", "fees"),
                 [[html_text(x["product"]), cc(x["mechanism"]), cc(x["queue"]), cc(x["settlement_time"]),
                   cc(x["gating"]), cc(x["fees"])]
                  for x in sorted(doc["redemption"], key=lambda x: id_key(x["product"]))])
    out += label("Eligibility:")
    out += table(("product", "restrictions"),
                 [[html_text(e["product"]), cc(e["restrictions"])]
                  for e in sorted(doc["eligibility"], key=lambda e: id_key(e["product"]))])
    return out


def _audits(r):
    cc = r.claim_cell
    return table(("auditor", "scope", "date", "report"),
                 [[cc(a["auditor"]), cc(a["scope"]), cc(a["date"]),
                   "--" if a["report_ref"] is None else r.sid(a["report_ref"])] for a in r.doc["audits"]])


def _size(r):
    return table(("product", "metric", "value", "as of"),
                 [[text(s["product"]), html_text(s["metric"]), r.claim_cell(s["value"]), text(s["as_of"])]
                  for s in r.doc["size"]])


def _history(r):
    return table(("date", "change", "evidence"),
                 [[text(h["date"]), html_text(h["change"], 200), r.evidence(h["evidence"])] for h in r.doc["history"]])


def _findings(r):
    findings = sorted(r.doc["findings"], key=id_key)
    out = []
    for title, pred in (("Discrepancies", lambda f: f["type"] == "discrepancy"),
                        ("Structural changes", lambda f: f["type"] == "structural_change"),
                        ("Other gaps", lambda f: f["type"] == "gap" and not f["blocking"])):
        out += h3(title)
        lines = [line for f in findings if pred(f) for line in r.finding_item(f)]
        out += ['<ul class="dd-list">'] + lines + ["</ul>"] if lines else [NONE]
    return out


def _questions(r):
    lines = ["[%s] %s" % (html_text(q["topic"]), html_text(q["question"], 200)) for q in r.doc["open_questions"]]
    return items(lines) if lines else []


def _sources(r):
    rows, ids = [], []
    for s in sorted(r.doc["sources"], key=id_key):
        fetch = html_text(s["fetch"])
        if s["archived"]:
            if s["fetch"] != "archived":
                fetch += ", archived"
            fetch += " (version %s)" % text(s["version_date"])
        href = html_url(s["url"])
        url = html_text(s["url"], 500)
        if href is not None:
            url = '<a href="%s" %s>%s</a>' % (href, LINK_ATTRS, url)
        ids.append("src-%s" % html_text(s["id"]))
        rows.append([html_text(s["id"]), html_text(s["source_type"]), html_text(s["origin"]), fetch,
                     text(s["retrieved_at"]), "%s -- %s" % (html_text(s["title"], 200), url),
                     html_text(s["note"], 200)])
    return table(("id", "type", "origin", "fetch", "retrieved", "title/url", "note"), rows, ids)


def _pre_text(body):
    body = body.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    return "\n".join(html_text(line) for line in body.split("\n"))


def _interventions(rounds):
    out = []
    for heading, body in rounds:
        out += h3(html_text(heading)) + ['<pre class="dd-pre">%s</pre>' % _pre_text(body)]
    return out


def _unmapped(r):
    lines = []
    for x in r.doc["x_unmapped"]:
        line = html_text(x["fact"], 200)
        if x["evidence"]:
            line += " (%s)" % r.evidence(x["evidence"])
        lines.append(line + " -- why unmapped: " + html_text(x["why_unmapped"], 120))
    return items(lines) if lines else []


def _legend_line(line):
    """Legend text with Markdown code spans turned into <code>."""
    parts = html_text(line[2:]).split("`")
    return "".join("<code>%s</code>" % part if i % 2 else part for i, part in enumerate(parts))


def _legend():
    out = items([_legend_line(line) for line in LEGEND])
    out += label("Badge key:")
    out += ['<ul class="dd-list dd-badge-key">']
    out += ["<li>%s %s</li>" % (badge(m), html_text(title)) for m, (_, title) in BADGES.items()]
    return out + ["</ul>"]


# --------------------------------------------------------------------------- page

def _asset(name):
    return (ASSETS / name).read_bytes().decode("utf-8")


def _fill(page, marker, value):
    if page.count(marker) != 1:
        raise ValueError("template marker %s must occur exactly once" % marker)
    return page.replace(marker, value)


def _css(name):
    css = _asset(name)
    if "</style" in css.lower():
        raise ValueError("%s must not contain </style" % name)
    return css


def render(doc, rounds=(), figures=None, rejected=()):
    """Render a structurally valid document; rounds = [(heading, text), ...];
    figures = {product id: sanitized SVG text}, embedded inline in section 6;
    rejected = N ids the analyst rejected, marked in Appendix D (final reports only)."""
    figures = figures or {}
    r = Renderer(doc)
    name = doc["project"]["name"]["value"]
    title = "RWA Due Diligence: " + (html_text(doc["run"]["slug"]) if name is None else fmt_value(name))

    sections = (
        ("s1", "1. Executive summary", ["<p>%s</p>" % html_text(doc["narrative"]["executive_summary"], 800)]
         if doc["narrative"]["executive_summary"] else []),
        ("s2", "2. Blocking gaps and materials to request", _blocking(r)),
        ("s3", "3. Products", _products(r)),
        ("s4", "4. Legal structure", _legal(r)),
        ("s5", "5. Yield source", _yield(r)),
        ("s6", "6. Fund flows", _flows(r, figures)),
        ("s7", "7. On-chain contracts and control", _onchain(r)),
        ("s8", "8. Redemption and eligibility", _redemption(r)),
        ("s9", "9. Audits", _audits(r)),
        ("s10", "10. Size", _size(r)),
        ("s11", "11. History", _history(r)),
        ("s12", "12. Findings", _findings(r)),
        ("s13", "13. Open questions", _questions(r)),
        ("s14", "14. Sources", _sources(r)),
        ("appendix-a", "Appendix A. Analyst interventions", _interventions(rounds)),
        ("appendix-b", "Appendix B. Unmapped facts", _unmapped(r)),
        ("appendix-c", "Appendix C. Legend", _legend()),
    )
    if doc["run"]["status"] == "final":
        sections += (("appendix-d", "Appendix D. Searches not run", _not_run(r, rejected)),)

    body = ['<main class="dd-report is--wrapper has--gutter">', '<header class="dd-header l--flow">',
            "<h1>%s</h1>" % title]
    body += _metadata(doc, rounds)
    if doc["run"]["status"] == "draft":
        body.append('<p class="dd-banner dd-banner--draft">DRAFT -- not finalized</p>')
    body += ["</header>", '<nav class="dd-toc">', "<ol>"]
    body += ['<li><a href="#%s">%s</a></li>' % (sid, heading) for sid, heading, _ in sections]
    body += ["</ol>", "</nav>"]
    for sid, heading, content in sections:
        cls = "dd-section l--flow"
        if sid == "s2":
            cls += " dd-panel dd-panel--blocking"
        body += ['<section id="%s" class="%s">' % (sid, cls), "<h2>%s</h2>" % heading]
        body += content or [NONE]
        body.append("</section>")
    body.append("</main>")

    page = _asset(TEMPLATE)
    page = _fill(page, "<!--DD:TITLE-->", title)
    page = _fill(page, "<!--DD:LISM_CSS-->", _css(LISM_CSS))
    page = _fill(page, "<!--DD:REPORT_CSS-->", _css(REPORT_CSS))
    return _fill(page, "<!--DD:BODY-->", "\n".join(body))
