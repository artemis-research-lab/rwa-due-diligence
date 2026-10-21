"""Review packet renderer (section 3.7, v0.5 section 5, v0.6.0 section 5, v0.7.0 section 5.1, v0.7.2 sections 1
and 2); deterministic."""

from lib import framework, qa, schema
from lib.textutil import finding_line, id_key, md_text, number_text, request_line, search_line, totals_text

FLAGS = framework.FLAGS

KINDS_B = ("holder_L1", "L1_L2", "within_L1", "sleeve_holding", "reserve_lookthrough")
OTHER = ("project", "yield", "redemption", "eligibility", "audits", "size", "onchain")


def _group(parts, doc):
    """Coverage group of the claim at parts, or None."""
    head = parts[0]
    if head == "entities" or (head == "strategies" and parts[2] in ("business_type", "deployment")):
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
    "# answer G<k>|D<k>|U<k>|R<k> : <text>",
    "# drop G<k>|D<k>|U<k>|R<k> : <reason>",
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


def amount_text(value):
    """`25000000`, `0.5`; `--` without a value."""
    return "--" if value is None else number_text(value)


def _cell(value, limit=None):
    """Free text cell; `--` for null."""
    return "--" if value is None else md_text(str(value), limit)


def _code(value):
    """Enum code cell (never escaped); `--` for null."""
    return "--" if value is None else str(value)


def components_table(doc):
    totals = framework.allocation_totals(doc)["strategies"]
    return _table(("strategy", "component", "deployment", "products", "counted totals"),
                  [[_title(t), t["component"], _deployment(doc, t), ", ".join(sorted(t["products"], key=id_key)),
                    totals_text(totals.get(t["id"], []))] for t in sorted(doc["strategies"], key=id_key)])


def _deployment(doc, t):
    claim = t["deployment"]
    flag = framework.flags(doc)[("strategies", doc["strategies"].index(t), "deployment")]
    return "%s [%s]" % (_code(claim["value"]), flag)


def amounts_table(doc):
    """Allocation rows with data as of, time basis and observed at (curator AC-03)."""
    return _table(("strategy", "interface", "entry", "kind", "value", "unit", "basis", "data as of", "time basis",
                   "observed at", "scope", "counted", "reason"),
                  [[row[0], row[2], _code(row[3]), row[4], amount_text(row[5]), _cell(row[6], 20), _code(row[7]),
                    "not established" if row[3] is not None and row[8] is None else _code(row[8]),
                    _code(row.time_basis), _code(row.observed_at), _cell(row[9], 200), "yes" if row[10] else "no",
                    row[11]]
                   for row in framework.allocation(doc)])


def section1_preview(doc):
    findings = {f["id"]: f for f in doc["findings"]}
    selected, _, rest = framework.critical_counts(doc)
    rows = [[f["id"], f["type"], "yes" if f["material"] else "no", "yes" if f["blocking"] else "no",
             ", ".join(f["k_checks"]) or "--", ", ".join(f["impact"]) or "--", md_text(f["statement"], 280)]
            for f in (findings[ident] for ident in framework.critical(doc))]
    out = _table(("id", "type", "material", "blocking", "k_checks", "impact", "statement"), rows)
    return out + ([""] if out else []) + ["%d shown; %d more open findings in section 6" % (selected, rest)]


def conflicts_table(doc):
    return _table(("finding", "conflict status", "scope match", "resolution", "subjects", "assertion sources"),
                  [[ident, status or "--", match, resolution, md_text(", ".join(subjects)) or "--",
                    ", ".join(sources) or "--"]
                   for ident, status, match, resolution, subjects, sources in framework.conflicts(doc)])


def provenance_table(doc):
    rows = []
    for parts, claim in schema.iter_claims(doc):
        if claim["origin"] is not None or claim["assurance"] is not None:
            rows.append([md_text(framework.claim_id(parts, doc)), claim["status"], _code(claim["origin"]),
                         _code(claim["assurance"]), ", ".join(claim["evidence"]) or "--"])
    return _table(("claim", "status", "origin", "assurance", "sources"), sorted(rows))


def qa_table(results):
    return _table(("id", "rule", "result", "target", "mapping", "detail"),
                  [[r["id"], md_text(r["rule"], 120), r["result"], _code(r["target"]), md_text(r["mapping"]) or "--",
                    md_text(r["detail"])] for r in results])


def migration_pending(doc):
    out = [finding_line(f, scope=True) for f in sorted(doc["findings"], key=id_key)
           if schema.is_placeholder(f["scope_note"])]
    for x in sorted(doc["interfaces"], key=id_key):
        out += ["- **%s.amounts[%d]** %s %s %s -- scope: %s"
                % (x["id"], j, a["basis"], amount_text(a["value"]["value"]), md_text(a["unit"], 20),
                   md_text(a["scope"], 200))
                for j, a in enumerate(x["amounts"]) if a["scope"] == schema.MIGRATED_AMOUNT_SCOPE]
    return out


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


def render(doc, round_no, qa_results=None):
    """Review packet of round round_no; qa_results defaults to qa.run(doc) without expectations."""
    slug = doc["run"]["slug"]
    findings = sorted(doc["findings"], key=id_key)
    searches = sorted(doc["next_searches"], key=id_key)
    results = qa.run(doc) if qa_results is None else qa_results

    def typed(kind, **kwargs):
        return [finding_line(f, **kwargs) for f in findings if f["type"] == kind]

    lines = ["# Review packet %s round %d" % (slug, round_no)]
    table = ["| group | %s |" % " | ".join(FLAGS), "|---|" + "---|" * len(FLAGS)]
    for name, row in coverage(doc).items():
        table.append("| %s | %s |" % (name, " | ".join(str(row[f]) for f in FLAGS)))
    _section(lines, "Coverage", table)
    _section(lines, "Section 1 preview", section1_preview(doc))
    _section(lines, "Portfolio components", components_table(doc))
    _section(lines, "Framework completeness", completeness_table(doc))
    _section(lines, "Three-layer chains", chain_lines(doc))
    _section(lines, "Amounts", amounts_table(doc))
    _section(lines, "Alternative paths", alternative_lines(doc))
    _section(lines, "Conflicts", conflicts_table(doc))
    _section(lines, "Provenance", provenance_table(doc))
    _section(lines, "QA", qa_table(results))
    _section(lines, "Migration checks pending", migration_pending(doc))
    _section(lines, "Material findings", [finding_line(f) for f in findings if f["material"]])
    _section(lines, "Blocking gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and f["blocking"]])
    _section(lines, "Other gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and not f["blocking"]])
    _section(lines, "Discrepancies", typed("discrepancy", subjects=True, scope=True))
    _section(lines, "Scope unresolved", typed("scope_unresolved", subjects=True, scope=True))
    _section(lines, "Unreconciled transactions", typed("unreconciled_transaction", subjects=True, scope=True))
    _section(lines, "Structural changes", typed("structural_change"))
    _section(lines, "Issuer requests", [request_line(q) for q in sorted(doc["issuer_requests"], key=id_key)])
    _section(lines, "Proposed next searches", [search_line(n) for n in searches])

    accept = " | ".join("accept %s" % n["id"] for n in searches) or "# no next searches proposed"
    _section(lines, "Directives template", ["```text", accept] + list(TEMPLATE_COMMENTS) + ["```"])
    return "\n".join(lines) + "\n"
