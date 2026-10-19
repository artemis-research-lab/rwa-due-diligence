"""Review packet renderer (section 3.7, v0.5 section 5); deterministic."""

from lib import framework
from lib.textutil import finding_line, id_key, md_text, request_line, search_line

FLAGS = framework.FLAGS

KINDS_B = ("holder_L1", "L1_L2", "within_L1")
KINDS_C = ("L2_L3", "within_L2", "within_L3")
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
    return None


GROUPS = ("A layers and entities", "B L1->L2", "C L2->L3 and default", "D holder rights", "E L3 business",
          "F flows", "O other")

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


def completeness_table(doc):
    header = ["strategy"] + ["%s %s" % (code, label) for code, label in framework.CHECKS]
    names = {t["id"]: t["name"] for t in doc["strategies"]}
    rows = [["%s %s" % (sid, md_text(names[sid], 80)) if names[sid] else sid] + [fl for _, _, fl in checks]
            for sid, checks in framework.completeness(doc)]
    out = ["| %s |" % " | ".join(header), "|" + "---|" * len(header)]
    return out + ["| %s |" % " | ".join(row) for row in rows]


def chain_lines(doc):
    out = []
    for t in sorted(doc["strategies"], key=id_key):
        prefix = "%s %s" % (t["id"], md_text(t["name"], 80)) if t["name"] else t["id"]
        out += ["- %s: %s" % (prefix, md_text(line)) for line in framework.chain_line(doc, t["id"])]
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
    _section(lines, "Framework completeness", completeness_table(doc))
    _section(lines, "Three-layer chains", chain_lines(doc))
    _section(lines, "Blocking gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and f["blocking"]])
    _section(lines, "Other gaps",
             [finding_line(f) for f in findings if f["type"] == "gap" and not f["blocking"]])
    _section(lines, "Discrepancies", [finding_line(f) for f in findings if f["type"] == "discrepancy"])
    _section(lines, "Structural changes",
             [finding_line(f) for f in findings if f["type"] == "structural_change"])
    _section(lines, "Issuer requests", [request_line(q) for q in sorted(doc["issuer_requests"], key=id_key)])
    _section(lines, "Proposed next searches", [search_line(n) for n in searches])

    accept = " | ".join("accept %s" % n["id"] for n in searches) or "# no next searches proposed"
    _section(lines, "Directives template", ["```text", accept] + list(TEMPLATE_COMMENTS) + ["```"])
    return "\n".join(lines) + "\n"
