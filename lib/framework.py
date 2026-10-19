"""Framework view (D40, D41, v0.6.0 section 3): evidence flags, conflicts, completeness checklist, chain lines,
allocation with its counting rule and the five questions.

Pure, deterministic functions over a structurally valid rwa-dd/2.1 document.
"""

import json

from lib import schema
from lib.textutil import id_key

FLAGS = schema.ENUMS["evidence_flag"]
# Worst first: the order used when several claims feed one checklist cell.
SEVERITY = ("CONFLICTING", "UNRESOLVED", "INFERRED", "THIRD_PARTY_REPORTED", "SELF_REPORTED", "CONFIRMED")
STATUS_FLAG = {"verified": "CONFIRMED", "self_reported": "SELF_REPORTED",
               "third_party_reported": "THIRD_PARTY_REPORTED", "inferred": "INFERRED", "not_found": "UNRESOLVED"}
SUBJECT_PREFIXES = ("E", "P", "T", "X", "Z")

CHECKS = (
    ("K1", "L1 legal counterparty"),
    ("K2", "L1->L2 legal claim"),
    ("K3", "L2->L3 method"),
    ("K4", "L2->L3 security"),
    ("K5", "Loss waterfall"),
    ("K6", "Holder look-through"),
    ("K7", "L3 business"),
)

# Components whose strategies get the completeness checklist and the five questions.
CORE = "CORE_CREDIT"

# --------------------------------------------------------------------------- 3.1 evidence flags

def _has_subject_id(value):
    ident = value.get("id") if isinstance(value, dict) else None
    return isinstance(ident, str) and ident[:1] in SUBJECT_PREFIXES


def subject_path(parts, doc):
    """Id path of the claim at parts, e.g. X3.security or Z1.coverage; None outside objects with an
    E/P/T/X/Z id.

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
    """Subject paths of the claims covered by any discrepancy finding's subjects (scope_unresolved never)."""
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


def core_strategies(doc):
    """CORE_CREDIT strategies in id order."""
    return [t for t in sorted(doc["strategies"], key=id_key) if t["component"] == CORE]


# --------------------------------------------------------------------------- 3.2 completeness

def completeness(doc):
    """[(strategy id, [(code, label, flag), ...]), ...] for CORE_CREDIT strategies in strategy id order."""
    by_parts = flags(doc)

    def picked(section, pred, *fields):
        return [by_parts[(section, i) + fields] for i, item in enumerate(doc[section]) if pred(item)]

    out = []
    for index, t in sorted(enumerate(doc["strategies"]), key=lambda item: id_key(item[1])):
        if t["component"] != CORE:
            continue
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
TARGET = {"holder_L1": "L1", "L1_L2": "L2", "L2_L3": "L3", "L3_L3O": "L3-O", "sleeve_holding": "issuer",
          "reserve_lookthrough": "reserve", "asset_sale": "transferee"}
# Forward kinds leaving each position (within_<position> is added for L1, L2 and L3).
FORWARD = {"L1": ("L1_L2", "sleeve_holding"), "L2": ("L2_L3", "asset_sale"), "L3": ("L3_L3O",),
           "issuer": ("reserve_lookthrough",)}
# Kinds that start a line when no earlier line used them, in this order, with the start position.
STARTS = (("L1_L2", "L1"), ("L2_L3", "L2"), ("sleeve_holding", "L1"), ("asset_sale", "L2"))
START_POSITION = dict(STARTS)


def alt_tag(x):
    """`A1a` for an interface in an alternative group, else None."""
    alt = x["alternative"]
    return None if alt["group"] is None else "%s%s" % (alt["group"], alt["option"])


def _hop(x):
    kind = x["kind"]
    if kind == "L1_L2":
        codes = [_code(x["route"]["value"]), _code(x["legal_class"]["value"])]
    elif kind == "L2_L3":
        codes = [_code(x["method"]["value"]), _code(x["security"]["value"])]
    elif kind == "asset_sale":
        codes = ["sale", _code(x["title_transfer"]["value"])]
    elif kind == "reserve_lookthrough":
        codes = ["look-through"]
    else:
        codes = [_code(x["legal_class"]["value"])]
    tag = alt_tag(x)
    if tag is not None:
        codes.append("alt " + tag)
    return "[%s]" % "; ".join(codes)


def _entity(doc, eid):
    return next((e for e in doc["entities"] if e["id"] == eid), None)


def _has_function(entity, strategy_id, layer=None, role=None):
    return entity is not None and any(
        fn["strategy"] in (strategy_id, None) and layer in (None, fn["layer"]) and role in (None, fn["role"])
        for fn in entity["functions"])


def entity_label(doc, eid, position):
    """Chain-line node label: `E1 Acme Ltd (L1)`; `E9 (?)` for an unknown entity."""
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
        if position in ("L1", "L2", "L3") and x["kind"] == "within_" + position:
            out.append((x, position))
        elif x["kind"] in FORWARD.get(position, ()):
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


def _render(doc, path, start_position):
    first = path[0][0]
    if first["kind"] == "holder_L1":
        parts = ["%s holders" % first["from"]]
    else:
        parts = [entity_label(doc, first["from"], start_position)]
    for j, (x, position) in enumerate(path):
        label = position
        if j + 1 < len(path) and position == "L1" and path[j + 1][0]["kind"] == "L2_L3":
            label = "L1/L2"
        parts += [_hop(x), entity_label(doc, x["to"], label)]
    return " -> ".join(parts)


def chain_line(doc, strategy_id):
    """One ASCII line per maximal path of the strategy, from token holders down to L3, L3-O, sleeve issuers and
    their reserves, and loan transferees.

    Lines start at holder_L1 interfaces; an L1_L2, L2_L3, sleeve_holding or asset_sale interface no line has
    used then starts a line of its own (in that order). Paths follow within-layer hops, the forward kinds of
    each position, and L2_L3 from an L1 node whose entity also holds an L2 function; a node already on the path
    is never entered again.
    """
    ifaces = sorted((x for x in doc["interfaces"] if x["strategy"] == strategy_id), key=id_key)
    lines = []
    used = set()

    def emit(start, start_position):
        for path in _walk(doc, ifaces, [(start, TARGET[start["kind"]])], strategy_id):
            used.update(x["id"] for x, _ in path)
            lines.append(_render(doc, path, start_position))

    for x in ifaces:
        if x["kind"] == "holder_L1":
            emit(x, None)
    for kind, position in STARTS:
        for x in ifaces:
            if x["kind"] == kind and x["id"] not in used:
                emit(x, position)
    return lines


# --------------------------------------------------------------------------- 3.4 allocation and counting

ALLOCATION_KINDS = ("L1_L2", "sleeve_holding", "reserve_lookthrough", "asset_sale")
FUNDING_KINDS = ("L1_L2", "sleeve_holding")
COUNTED_BASIS = "GROSS_FUNDED"
NO_CURRENCY = "n/d"


def _reason(x):
    tag = alt_tag(x)
    basis = x["amount_basis"]
    if tag is not None:
        return "alternative " + tag
    if basis is not None and basis != COUNTED_BASIS:
        return "basis " + basis
    if x["amount"]["value"] is None or basis is None:
        return "no amount"
    if x["kind"] not in FUNDING_KINDS:
        return "not a funding edge"
    return "counted"


def allocation(doc):
    """[(strategy id, component, interface id, kind, amount, currency, basis, counted, reason), ...] for every
    interface of an allocation kind, in strategy then interface id order."""
    components = {t["id"]: t["component"] for t in doc["strategies"]}
    rows = []
    for x in sorted(doc["interfaces"], key=lambda x: (id_key(x["strategy"]), id_key(x))):
        if x["kind"] not in ALLOCATION_KINDS:
            continue
        reason = _reason(x)
        rows.append((x["strategy"], components.get(x["strategy"]), x["id"], x["kind"], x["amount"]["value"],
                     x["currency"]["value"], x["amount_basis"], reason == "counted", reason))
    return rows


def currency_key(value):
    """Grouping key of a currency claim value: the string itself, `n/d` for null, JSON text otherwise."""
    if value is None:
        return NO_CURRENCY
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def allocation_totals(doc):
    """{"strategies": {T id: {currency: sum}}, "components": {component: {currency: sum}}} of counted amounts;
    the only place amounts are summed."""
    out = {"strategies": {}, "components": {}}
    for sid, component, _, _, amount, currency, _, counted, _ in allocation(doc):
        if not counted:
            continue
        key = currency_key(currency)
        for scope, name in (("strategies", sid), ("components", component)):
            bucket = out[scope].setdefault(name, {})
            bucket[key] = bucket.get(key, 0) + amount
    return out


# --------------------------------------------------------------------------- 3.5 five questions

QUESTIONS = ("Who holds investor capital?", "Who deploys credit?", "Who receives financing?", "Who must repay?",
             "Who can enforce the claim?")


def plain_value(value):
    """Claim value as plain text (lists joined with `, `)."""
    if isinstance(value, list):
        return ", ".join(plain_value(v) for v in value)
    if isinstance(value, dict):
        return ", ".join("%s=%s" % (k, plain_value(v)) for k, v in value.items())
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    return str(value)


def _join(items):
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return "; ".join(out)


def five_questions(doc, strategy_id):
    """[(question, answer), ...] for one CORE_CREDIT strategy; `UNRESOLVED` for an empty answer."""
    by_parts = flags(doc)
    indexed = sorted(((i, x) for i, x in enumerate(doc["interfaces"]) if x["strategy"] == strategy_id),
                     key=lambda item: id_key(item[1]))
    strategy = next(t for t in doc["strategies"] if t["id"] == strategy_id)

    def tagged(i, x, eid, position):
        tail = by_parts[("interfaces", i, "legal_class")]
        tag = alt_tag(x)
        if tag is not None:
            tail += "; alt " + tag
        return "%s [%s]" % (entity_label(doc, eid, position), tail)

    def ends(kind, end, position):
        return [tagged(i, x, x[end], position) for i, x in indexed if x["kind"] == kind]

    deployers = ends("L1_L2", "to", "L2") + [
        tagged(i, x, x["from"], "L1/L2") for i, x in indexed
        if x["kind"] == "L2_L3" and _has_function(_entity(doc, x["from"]), strategy_id, layer="L1")]
    receivers = ends("L2_L3", "to", "L3")
    sources = ends("L3_L3O", "to", "L3-O")
    repay = [_join(receivers)] if receivers else []
    if sources:
        repay.append("cash flows from: " + _join(sources))

    claims = []
    for i, h in enumerate(doc["holder_rights"]):
        if h["product"] in strategy["products"] and h["claim_against"]["value"] is not None:
            claims.append((("holder_rights", i, "claim_against"), h["claim_against"]))
    for i, x in indexed:
        if x["kind"] == "L2_L3" and x["enforcement"]["value"] is not None:
            claims.append((("interfaces", i, "enforcement"), x["enforcement"]))
    enforce = _join("%s [%s]" % (plain_value(c["value"]), by_parts[parts]) for parts, c in claims)

    answers = [_join(ends("holder_L1", "to", "L1")), _join(deployers), _join(receivers), "; ".join(repay),
               enforce]
    return [(q, a or "UNRESOLVED") for q, a in zip(QUESTIONS, answers)]
