"""Review packet renderer (section 3.7); deterministic."""

from lib import schema
from lib.textutil import finding_line, id_key, search_line

# Coverage dimension -> predicate on claim path parts.
DIMENSIONS = (
    ("L legal", lambda p: p[0] in schema.LEGAL_SECTIONS),
    ("Y yield", lambda p: p[0] in ("yield", "redemption")),
    ("F flows", lambda p: p[:2] == ("flows", "edges") and p[-1] == "claim"),
    ("C onchain", lambda p: p[0] == "onchain"),
    ("P project", lambda p: p[0] == "project"),
)

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
    counts = {name: {s: 0 for s in schema.ENUMS["claim_status"]} for name, _ in DIMENSIONS}
    for parts, claim in schema.iter_claims(doc):
        for name, pred in DIMENSIONS:
            if pred(parts):
                counts[name][claim["status"]] += 1
    return counts


def _section(lines, title, body):
    lines += ["", "## " + title, ""]
    lines += body or ["- none"]


def render(doc, round_no):
    slug = doc["run"]["slug"]
    findings = sorted(doc["findings"], key=id_key)
    searches = sorted(doc["next_searches"], key=id_key)
    statuses = schema.ENUMS["claim_status"]

    lines = ["# Review packet %s round %d" % (slug, round_no)]
    table = ["| dimension | %s |" % " | ".join(statuses), "|---|" + "---|" * len(statuses)]
    for name, row in coverage(doc).items():
        table.append("| %s | %s |" % (name, " | ".join(str(row[s]) for s in statuses)))
    _section(lines, "Coverage", table)
    _section(lines, "Blocking gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and f["blocking"]])
    _section(lines, "Other gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and not f["blocking"]])
    _section(lines, "Discrepancies", [finding_line(f) for f in findings if f["type"] == "discrepancy"])
    _section(lines, "Structural changes",
             [finding_line(f) for f in findings if f["type"] == "structural_change"])
    _section(lines, "Proposed next searches", [search_line(n) for n in searches])

    accept = " | ".join("accept %s" % n["id"] for n in searches) or "# no next searches proposed"
    _section(lines, "Directives template", ["```text", accept] + list(TEMPLATE_COMMENTS) + ["```"])
    return "\n".join(lines) + "\n"
