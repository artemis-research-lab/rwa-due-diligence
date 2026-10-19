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

# --------------------------------------------------------------------------- 3.1 evidence flags

def _has_subject_id(value):
    ident = value.get("id") if isinstance(value, dict) else None
    return isinstance(ident, str) and ident[:1] in SUBJECT_PREFIXES


def subject_path(parts, doc):
    """Id path of the claim at parts, e.g. X3.security; None outside objects with an E/P/T/X id.

    Holder-rights claims take their product's id: P1.holder_rights.look_through.
    """
    if parts and parts[0] == "holder_rights":
        fields = [p for p in parts[2:] if not isinstance(p, int)]
        return ".".join([doc["holder_rights"][parts[1]]["product"], "holder_rights"] + fields)
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


# Position of the node an interface leads to; within_Lk keeps the position of its from node.
TARGET = {"holder_L1": "L1", "L1_L2": "L2", "L2_L3": "L3"}
FORWARD = {"L1": "L1_L2", "L2": "L2_L3"}
START_POSITION = {"L1_L2": "L1", "L2_L3": "L2"}


def _hop(x):
    if x["kind"] == "L1_L2":
        codes = [x["route"]["value"], x["legal_class"]["value"]]
    elif x["kind"] == "L2_L3":
        codes = [x["method"]["value"], x["security"]["value"]]
    else:
        codes = [x["legal_class"]["value"]]
    return "[%s]" % "; ".join(_code(c) for c in codes)


def _entity(doc, eid):
    return next((e for e in doc["entities"] if e["id"] == eid), None)


def _has_function(entity, strategy_id, layer=None, role=None):
    return entity is not None and any(
        fn["strategy"] in (strategy_id, None) and layer in (None, fn["layer"]) and role in (None, fn["role"])
        for fn in entity["functions"])


def _entity_label(doc, eid, position):
    entity = _entity(doc, eid)
    if entity is None:
        return "%s (?)" % eid
    name = entity["legal_name"]["value"]
    head = eid if name is None else "%s %s" % (eid, _code(name))
    return "%s (%s)" % (head, position)


def _continuations(doc, ifaces, node, position, strategy_id):
    """[(interface, next position)] leaving node at position, in interface-id order."""
    out = []
    for x in ifaces:
        if x["from"] != node:
            continue
        if x["kind"] == "within_" + position:
            out.append((x, position))
        elif x["kind"] == FORWARD.get(position):
            out.append((x, TARGET[x["kind"]]))
        elif (position == "L1" and x["kind"] == "L2_L3"
              and _has_function(_entity(doc, node), strategy_id, layer="L2")):
            out.append((x, "L3"))
    return out


def _walk(doc, ifaces, steps, strategy_id):
    """Maximal paths extending steps, a list of (interface, position reached), depth first in id order."""
    x, position = steps[-1]
    seen = {steps[0][0]["from"]} | {s[0]["to"] for s in steps}
    nexts = [(y, p) for y, p in _continuations(doc, ifaces, x["to"], position, strategy_id) if y["to"] not in seen]
    if not nexts:
        return [steps]
    return [path for step in nexts for path in _walk(doc, ifaces, steps + [step], strategy_id)]


def _render(doc, path, start_position, strategy_id):
    first = path[0][0]
    if first["kind"] == "holder_L1":
        parts = ["%s holders" % first["from"]]
    else:
        parts = [_entity_label(doc, first["from"], start_position)]
    for j, (x, position) in enumerate(path):
        label = position
        if j + 1 < len(path) and position == "L1" and path[j + 1][0]["kind"] == "L2_L3":
            label = "L1/L2"
        elif x["kind"] == "within_L3" and _has_function(_entity(doc, x["to"]), strategy_id, role="ultimate_obligor"):
            label = "L3-O"
        parts += [_hop(x), _entity_label(doc, x["to"], label)]
    return " -> ".join(parts)


def chain_line(doc, strategy_id):
    """One ASCII line per maximal path of the strategy, from token holders down to L3 and its ultimate obligors.

    Lines start at holder_L1 interfaces; an L1_L2 or L2_L3 interface no line has used then starts a line of its
    own. Paths follow within-layer hops, the forward kind of each layer, and L2_L3 from an L1 node whose entity
    also holds an L2 function; a node already on the path is never entered again.
    """
    ifaces = sorted((x for x in doc["interfaces"] if x["strategy"] == strategy_id), key=id_key)
    lines = []
    used = set()

    def emit(start, start_position):
        for path in _walk(doc, ifaces, [(start, TARGET[start["kind"]])], strategy_id):
            used.update(x["id"] for x, _ in path)
            lines.append(_render(doc, path, start_position, strategy_id))

    for x in ifaces:
        if x["kind"] == "holder_L1":
            emit(x, None)
    for x in ifaces:
        if x["kind"] in START_POSITION and x["id"] not in used:
            emit(x, START_POSITION[x["kind"]])
    return lines
