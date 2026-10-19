"""Review packet renderer (section 3.7, v0.5 section 5, v0.6.0 section 5); deterministic."""

from lib import framework, schema
from lib.textutil import finding_line, id_key, md_text, number_text, request_line, search_line, totals_text

FLAGS = framework.FLAGS

KINDS_B = ("holder_L1", "L1_L2", "within_L1", "sleeve_holding", "reserve_lookthrough")
OTHER = ("project", "yield", "redemption", "eligibility", "audits", "size", "onchain")


def _group(parts, doc):
    """Coverage group of the claim at parts, or None."""
    head = parts[0]
    if head == "entities" or (head == "strategies" and parts[2] == "business_type"):
        return "A layers and entities"
    if head == "interfaces":
        kind = doc["interfaces"][parts[1]]["kind"]
        return "B L1->L2" if kind in KINDS_B else "C L2->L3 and default"
    if head == "strategies" and parts[2] == "default_path":
        return "C L2->L3 and default"
    if head == "holder_rights":
        return "D holder rights"
    if head == "strategies" and parts[2] == "l3_business":
        return "E L3 business"
    if parts[:2] == ("flows", "edges"):
        return "F flows"
    if head in OTHER:
        return "O other"
    if head == "supports":
        return "S supports"
    return None


GROUPS = ("A layers and entities", "B L1->L2", "C L2->L3 and default", "D holder rights", "E L3 business",
          "F flows", "O other", "S supports")

TEMPLATE_COMMENTS = (
    "# reject N<k>",
    "# add-source <url-or-path> : <why>",
    "# answer G<k>|D<k> : <text>",
    "# drop G<k>|D<k> : <reason>",
    "# note <text>",
    "# priority N<a>,N<b>,...",
    "# limit N<k> <calls 1..20>",
    "# allow-fallback N<k> archive|browser",
    "# finalize",
)


def coverage(doc):
    counts = {name: {f: 0 for f in FLAGS} for name in GROUPS}
    for parts, fl in framework.flags(doc).items():
        name = _group(parts, doc)
        if name is not None:
            counts[name][fl] += 1
    return counts


def _title(t):
    return "%s %s" % (t["id"], md_text(t["name"], 80)) if t["name"] else t["id"]


def completeness_table(doc):
    header = ["strategy"] + ["%s %s" % (code, label) for code, label in framework.CHECKS]
    names = {t["id"]: t for t in doc["strategies"]}
    rows = [[_title(names[sid])] + [fl for _, _, fl in checks] for sid, checks in framework.completeness(doc)]
    if not rows:
        return []
    out = ["| %s |" % " | ".join(header), "|" + "---|" * len(header)]
    return out + ["| %s |" % " | ".join(row) for row in rows]


def chain_lines(doc):
    out = []
    for t in sorted(doc["strategies"], key=id_key):
        out += ["- %s: %s" % (_title(t), md_text(line)) for line in framework.chain_line(doc, t["id"])]
    return out


def _table(header, rows):
    if not rows:
        return []
    out = ["| %s |" % " | ".join(header), "|" + "---|" * len(header)]
    return out + ["| %s |" % " | ".join(row) for row in rows]


def amount_text(amount, currency):
    """`25000000 USD`, `25000000` without a currency, `--` without an amount."""
    if amount is None:
        return "--"
    text = number_text(amount)
    return text if currency is None else "%s %s" % (text, md_text(framework.currency_key(currency)))


def components_table(doc):
    totals = framework.allocation_totals(doc)["strategies"]
    return _table(("strategy", "component", "products", "counted total"),
                  [[_title(t), t["component"], ", ".join(sorted(t["products"], key=id_key)),
                    totals_text(totals.get(t["id"], {}))] for t in sorted(doc["strategies"], key=id_key)])


def allocation_table(doc):
    return _table(("strategy", "interface", "kind", "amount", "basis", "counted", "reason"),
                  [[sid, xid, kind, amount_text(amount, currency), basis or "--", "yes" if counted else "no",
                    reason] for sid, _, xid, kind, amount, currency, basis, counted, reason
                   in framework.allocation(doc)])


def alternative_lines(doc):
    """`- A1 (T2): a X11; b X12` per alternative group, in group then option order."""
    groups = {}
    for x in sorted(doc["interfaces"], key=id_key):
        alt = x["alternative"]
        if alt["group"] is not None:
            groups.setdefault(alt["group"], {}).setdefault(alt["option"], []).append(x)
    out = []
    for group in sorted(groups, key=id_key):
        options = groups[group]
        strategies = sorted({x["strategy"] for xs in options.values() for x in xs}, key=id_key)
        out.append("- %s (%s): %s" % (group, ", ".join(strategies), "; ".join(
            "%s %s" % (option, ", ".join(x["id"] for x in options[option])) for option in sorted(options))))
    return out


def _section(lines, title, body):
    lines += ["", "## " + title, ""]
    lines += body or ["- none"]


def render(doc, round_no):
    slug = doc["run"]["slug"]
    findings = sorted(doc["findings"], key=id_key)
    searches = sorted(doc["next_searches"], key=id_key)

    lines = ["# Review packet %s round %d" % (slug, round_no)]
    table = ["| group | %s |" % " | ".join(FLAGS), "|---|" + "---|" * len(FLAGS)]
    for name, row in coverage(doc).items():
        table.append("| %s | %s |" % (name, " | ".join(str(row[f]) for f in FLAGS)))
    _section(lines, "Coverage", table)
    _section(lines, "Portfolio components", components_table(doc))
    _section(lines, "Framework completeness", completeness_table(doc))
    _section(lines, "Three-layer chains", chain_lines(doc))
    _section(lines, "Allocation", allocation_table(doc))
    _section(lines, "Alternative paths", alternative_lines(doc))
    _section(lines, "Material findings", [finding_line(f) for f in findings if f["material"]])
    _section(lines, "Scope checks pending",
             [finding_line(f) for f in findings
              if f["type"] == "discrepancy" and f["scope_note"] == schema.MIGRATED_SCOPE_NOTE])
    _section(lines, "Blocking gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and f["blocking"]])
    _section(lines, "Other gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and not f["blocking"]])
    _section(lines, "Discrepancies",
             [finding_line(f, subjects=True, scope=True) for f in findings if f["type"] == "discrepancy"])
    _section(lines, "Scope unresolved",
             [finding_line(f, subjects=True) for f in findings if f["type"] == "scope_unresolved"])
    _section(lines, "Structural changes",
             [finding_line(f) for f in findings if f["type"] == "structural_change"])
    _section(lines, "Issuer requests", [request_line(q) for q in sorted(doc["issuer_requests"], key=id_key)])
    _section(lines, "Proposed next searches", [search_line(n) for n in searches])

    accept = " | ".join("accept %s" % n["id"] for n in searches) or "# no next searches proposed"
    _section(lines, "Directives template", ["```text", accept] + list(TEMPLATE_COMMENTS) + ["```"])
    return "\n".join(lines) + "\n"
