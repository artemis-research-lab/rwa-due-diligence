"""Framework view (D40, D41): evidence flags, conflicts, completeness checklist and chain lines.

Pure, deterministic functions over a structurally valid rwa-dd/2.0 document.
"""

from lib import schema
from lib.textutil import id_key

FLAGS = schema.ENUMS["evidence_flag"]
# Worst first: the order used when several claims feed one checklist cell.
SEVERITY = ("CONFLICTING", "UNRESOLVED", "PARTIALLY_VERIFIED", "CONFIRMED")
STATUS_FLAG = {"verified": "CONFIRMED", "self_reported": "PARTIALLY_VERIFIED", "inferred": "PARTIALLY_VERIFIED",
               "not_found": "UNRESOLVED"}
SUBJECT_PREFIXES = ("E", "P", "T", "X")

CHECKS = (
    ("K1", "L1 legal counterparty"),
    ("K2", "L1->L2 legal claim"),
    ("K3", "L2->L3 method"),
    ("K4", "L2->L3 security"),
    ("K5", "Loss waterfall"),
    ("K6", "Holder look-through"),
    ("K7", "L3 business"),
)

CHAIN_ORDER = ("holder_L1", "L1_L2", "L2_L3")


# --------------------------------------------------------------------------- 3.1 evidence flags

def _has_subject_id(value):
    ident = value.get("id") if isinstance(value, dict) else None
    return isinstance(ident, str) and ident[:1] in SUBJECT_PREFIXES


def subject_path(parts, doc):
    """Id path of the claim at parts, e.g. X3.security; None outside objects with an E/P/T/X id."""
    node = doc
    path = None
    for part in parts:
        node = node[part]
        if isinstance(part, int):
            if _has_subject_id(node):
                path = [node["id"]]
        elif path is not None:
            path.append(part)
    return ".".join(path) if path else None


def _covers(subject, path):
    return path == subject or path.startswith(subject + ".")


def conflicted(doc):
    """Subject paths of the claims covered by any discrepancy finding's subjects."""
    subjects = [s for f in doc["findings"] if f["type"] == "discrepancy" for s in f["subjects"]]
    out = set()
    for parts, _ in schema.iter_claims(doc):
        path = subject_path(parts, doc)
        if path is not None and any(_covers(s, path) for s in subjects):
            out.add(path)
    return out


def flag(claim, conflicted_flag):
    if conflicted_flag:
        return "CONFLICTING"
    return STATUS_FLAG[claim["status"]]


def flags(doc):
    """{path_parts: flag} for every claim."""
    hit = conflicted(doc)
    return {parts: flag(claim, subject_path(parts, doc) in hit) for parts, claim in schema.iter_claims(doc)}


def worst(values):
    """Worst flag of values by SEVERITY; UNRESOLVED when there is none."""
    values = list(values)
    if not values:
        return "UNRESOLVED"
    return min(values, key=SEVERITY.index)


# --------------------------------------------------------------------------- 3.2 completeness

def completeness(doc):
    """[(strategy id, [(code, label, flag), ...]), ...] in strategy id order."""
    by_parts = flags(doc)

    def picked(section, pred, *fields):
        return [by_parts[(section, i) + fields] for i, item in enumerate(doc[section]) if pred(item)]

    out = []
    for index, t in sorted(enumerate(doc["strategies"]), key=lambda item: id_key(item[1])):
        sid = t["id"]
        counterparty = []
        for i, e in enumerate(doc["entities"]):
            if any(fn["role"] == "holder_counterparty" and fn["strategy"] in (sid, None) for fn in e["functions"]):
                counterparty.append(by_parts[("entities", i, "legal_name")])

        def of_kind(kind):
            return lambda x: x["strategy"] == sid and x["kind"] == kind

        cells = [
            counterparty,
            picked("interfaces", of_kind("L1_L2"), "legal_class"),
            picked("interfaces", of_kind("L2_L3"), "method"),
            picked("interfaces", of_kind("L2_L3"), "security"),
            [by_parts[("strategies", index, "default_path", "loss_waterfall")]],
            picked("holder_rights", lambda h: h["product"] in t["products"], "look_through"),
            [by_parts[("strategies", index, "l3_business", "description")]],
        ]
        out.append((sid, [(code, label, worst(cell)) for (code, label), cell in zip(CHECKS, cells)]))
    return out


# --------------------------------------------------------------------------- 3.3 chain lines

def _code(value):
    if value is None:
        return "?"
    if isinstance(value, list):
        return "+".join(str(v) for v in value) if value else "?"
    return str(value)


def _hop(x):
    if x["kind"] == "holder_L1":
        codes = [x["legal_class"]["value"]]
    elif x["kind"] == "L1_L2":
        codes = [x["route"]["value"], x["legal_class"]["value"]]
    else:
        codes = [x["method"]["value"], x["security"]["value"]]
    return "[%s]" % "; ".join(_code(c) for c in codes)


def _entity_label(doc, eid, strategy_id):
    entity = next((e for e in doc["entities"] if e["id"] == eid), None)
    if entity is None:
        return eid
    name = entity["legal_name"]["value"]
    layer = next((fn["layer"] for fn in entity["functions"] if fn["strategy"] in (strategy_id, None)), "?")
    head = eid if name is None else "%s %s" % (eid, _code(name))
    return "%s (%s)" % (head, layer)


def _paths(chain_ifaces, start):
    """Interface sequences starting with start, following the next kinds in CHAIN_ORDER."""
    rank = CHAIN_ORDER.index(start["kind"])
    nexts = []
    for kind in CHAIN_ORDER[rank + 1:]:
        nexts = [x for x in chain_ifaces if x["kind"] == kind and x["from"] == start["to"]]
        if nexts:
            break
    if not nexts:
        return [[start]]
    return [[start] + rest for x in nexts for rest in _paths(chain_ifaces, x)]


def chain_line(doc, strategy_id):
    """One ASCII line per holder-to-L3 path of the strategy (within_* interfaces are skipped).

    Paths start at holder_L1 interfaces; an L1_L2 or L2_L3 interface not reached from an earlier hop starts a
    line of its own, so every interface of the chain kinds appears.
    """
    chain_ifaces = sorted((x for x in doc["interfaces"] if x["strategy"] == strategy_id
                           and x["kind"] in CHAIN_ORDER), key=id_key)
    lines = []
    reached = set()
    for kind in CHAIN_ORDER:
        for start in chain_ifaces:
            if start["kind"] != kind or start["id"] in reached:
                continue
            for path in _paths(chain_ifaces, start):
                reached.update(x["id"] for x in path)
                first = path[0]
                head = ("%s holders" % first["from"] if first["kind"] == "holder_L1"
                        else _entity_label(doc, first["from"], strategy_id))
                parts = [head]
                for x in path:
                    parts += [_hop(x), _entity_label(doc, x["to"], strategy_id)]
                lines.append(" -> ".join(parts))
    return lines
