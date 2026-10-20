"""Framework view (D40, D41, v0.6.0 section 3, v0.7.0 section 3): claim ids, evidence flags, conflict statuses,
completeness checklist, chain lines, allocation with its counting rule, the six questions, the section 1
selection and path resolution.

Pure, deterministic functions over a structurally valid rwa-dd/2.2 document.
"""

import json
import re

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

# --------------------------------------------------------------------------- 3.1/3.2 claim ids and flags

def _has_subject_id(value):
    ident = value.get("id") if isinstance(value, dict) else None
    return isinstance(ident, str) and ident[:1] in SUBJECT_PREFIXES


def claim_id(parts, doc):
    """Id-based path of the claim at parts: the nearest ancestor with an E/P/T/X/Z id followed by the field path
    below it, `[n]` for array positions (X2.amounts[0].value, P1.holder_rights.look_through); the document path
    (project.name, yield[0].gross_yield) when no ancestor has such an id."""
    if parts and parts[0] == "holder_rights":
        return schema.format_path(("%s.holder_rights" % doc["holder_rights"][parts[1]]["product"],) + parts[2:])
    node = doc
    start = None
    ident = None
    for k, part in enumerate(parts):
        node = node[part]
        if isinstance(part, int) and _has_subject_id(node):
            start, ident = k + 1, node["id"]
    if ident is None:
        return schema.format_path(parts)
    return schema.format_path((ident,) + tuple(parts[start:]))


def subject_path(parts, doc):
    """Claim id of the claim at parts when it starts with an E/P/T/X/Z id, else None."""
    path = claim_id(parts, doc)
    return path if path[:1] in SUBJECT_PREFIXES and re.match(r"^[A-Z][0-9]", path) else None


def _covers(subject, path):
    return path == subject or path.startswith(subject + ".") or path.startswith(subject + "[")


def conflicting_finding(finding):
    """True for an open discrepancy whose scope was matched: the only finding that flags claims."""
    return (finding["type"] == "discrepancy" and finding["scope_match"] == "matched"
            and finding["resolution"]["status"] == "open")


def conflicted(doc):
    """Claim ids covered by the subjects of open matched discrepancies (other findings never)."""
    subjects = [s for f in doc["findings"] if conflicting_finding(f) for s in f["subjects"]]
    out = set()
    if not subjects:
        return out
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


def flags_by_id(doc):
    """{claim id: flag} for every claim, sorted by claim id."""
    hit = conflicted(doc)
    out = {}
    for parts, claim in schema.iter_claims(doc):
        cid = claim_id(parts, doc)
        out[cid] = flag(claim, cid in hit)
    return dict(sorted(out.items()))


def conflict_status(finding):
    """CONFLICTING, RESOLVED, SCOPE_UNRESOLVED, UNRECONCILED_TRANSACTION or None (gaps, structural changes)."""
    kind = finding["type"]
    if kind == "discrepancy":
        if finding["resolution"]["status"] == "resolved":
            return "RESOLVED"
        return "CONFLICTING" if finding["scope_match"] == "matched" else None
    if kind == "scope_unresolved":
        return "SCOPE_UNRESOLVED"
    if kind == "unreconciled_transaction":
        return "UNRECONCILED_TRANSACTION"
    return None


def conflicts(doc):
    """[(finding id, conflict status, scope_match, resolution status, subjects, assertion sources), ...] for
    D, U and R findings in id order."""
    return [(f["id"], conflict_status(f), f["scope_match"], f["resolution"]["status"], list(f["subjects"]),
             [a["source"] for a in f["assertions"]])
            for f in sorted(doc["findings"], key=id_key) if f["id"][0] in "DUR"]


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


def _hop(x, loan_flag=None):
    kind = x["kind"]
    if kind == "L1_L2":
        codes = [_code(x["route"]["value"]), _code(x["legal_class"]["value"])]
    elif kind == "L2_L3":
        codes = [_code(x["method"]["value"]), _code(x["security"]["value"])]
    elif kind == "asset_sale":
        codes = ["sale", _code(x["title_transfer"]["value"]), "loan " + loan_flag]
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


def _render(doc, path, start_position, by_parts):
    first = path[0][0]
    if first["kind"] == "holder_L1":
        parts = ["%s holders" % first["from"]]
    else:
        parts = [entity_label(doc, first["from"], start_position)]
    for j, (x, position) in enumerate(path):
        label = position
        if j + 1 < len(path) and position == "L1" and path[j + 1][0]["kind"] == "L2_L3":
            label = "L1/L2"
        loan = None
        if x["kind"] == "asset_sale":
            loan = by_parts[("interfaces", doc["interfaces"].index(x), "loan_identity")]
        parts += [_hop(x, loan), entity_label(doc, x["to"], label)]
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
    by_parts = flags(doc) if any(x["kind"] == "asset_sale" for x in ifaces) else {}
    lines = []
    used = set()

    def emit(start, start_position):
        for path in _walk(doc, ifaces, [(start, TARGET[start["kind"]])], strategy_id):
            used.update(x["id"] for x, _ in path)
            lines.append(_render(doc, path, start_position, by_parts))

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
COUNTABLE = schema.COUNTABLE
ROW_FIELDS = ("strategy", "component", "interface", "entry", "kind", "value", "unit", "basis", "as_of", "scope",
              "counted", "reason")


class Row(tuple):
    """One allocation row (ROW_FIELDS); compares as a plain tuple and also carries the valuation basis that
    total_key needs."""

    def __new__(cls, fields, valuation_basis=None):
        row = super().__new__(cls, fields)
        row.valuation_basis = valuation_basis
        return row

    def as_object(self):
        out = dict(zip(ROW_FIELDS, self))
        out["valuation_basis"] = self.valuation_basis
        return out


def _reason(x, amount):
    tag = alt_tag(x)
    if tag is not None:
        return "alternative " + tag
    if x["kind"] not in FUNDING_KINDS:
        return "not a funding edge"
    if amount is None:
        return "no amount"
    if amount["basis"] not in COUNTABLE:
        return "basis %s not counted" % amount["basis"]
    if amount["value"]["value"] is None:
        return "no amount"
    if amount["as_of"] is None:
        return "no observation time"
    if amount["scope"] == schema.MIGRATED_AMOUNT_SCOPE:
        return "migrated scope"
    return "counted"


def allocation(doc):
    """One Row per amount entry on interfaces of an allocation kind, in strategy, interface id and entry order;
    an interface without amounts gives one row with entry None and reason `no amount`."""
    components = {t["id"]: t["component"] for t in doc["strategies"]}
    rows = []
    for x in sorted(doc["interfaces"], key=lambda x: (id_key(x["strategy"]), id_key(x))):
        if x["kind"] not in ALLOCATION_KINDS:
            continue
        head = (x["strategy"], components.get(x["strategy"]), x["id"])
        if not x["amounts"]:
            rows.append(Row(head + (None, x["kind"], None, None, None, None, None, False, "no amount")))
            continue
        for j, a in enumerate(x["amounts"]):
            reason = _reason(x, a)
            rows.append(Row(head + (j, x["kind"], a["value"]["value"], a["unit"], a["basis"], a["as_of"], a["scope"],
                                    reason == "counted", reason), a["valuation_basis"]))
    return rows


def total_key(row):
    """(basis, unit, observation date YYYY-MM-DD, valuation basis or "") of an allocation row."""
    as_of = row[8]
    return (row[7], row[6], as_of[:10] if as_of else "", row.valuation_basis or "")


def total_label(key, value):
    """`<sum> <unit> <BASIS> @<date>`."""
    basis, unit, date, _ = key
    return "%s %s %s @%s" % (json.dumps(value), unit, basis, date)


def _sum_rows(rows):
    sums = {}
    for row in rows:
        key = total_key(row)
        sums[key] = sums.get(key, 0) + row[5]
    return [{"basis": k[0], "unit": k[1], "as_of": k[2], "valuation_basis": k[3] or None, "sum": sums[k],
             "label": total_label(k, sums[k])} for k in sorted(sums)]


def allocation_totals(doc):
    """{"strategies": {T id: [total, ...]}, "components": {component: [...]}, "products": {P id: [...]}} of
    counted amounts, each total {basis, unit, as_of, valuation_basis, sum, label} grouped by total_key and
    ordered by key; a product total fed by a strategy that serves several products carries shared true.
    The only place amounts are summed."""
    counted = [row for row in allocation(doc) if row[10]]
    out = {"strategies": {}, "components": {}, "products": {}}
    for t in sorted(doc["strategies"], key=id_key):
        rows = [r for r in counted if r[0] == t["id"]]
        if rows:
            out["strategies"][t["id"]] = _sum_rows(rows)
    for component in schema.ENUMS["component"]:
        rows = [r for r in counted if r[1] == component]
        if rows:
            out["components"][component] = _sum_rows(rows)
    for p in sorted(doc["project"]["products"], key=id_key):
        serving = [t for t in doc["strategies"] if p["id"] in t["products"]]
        rows = [r for r in counted if r[0] in {t["id"] for t in serving}]
        if rows:
            shared = any(len(t["products"]) > 1 for t in serving if any(r[0] == t["id"] for r in rows))
            out["products"][p["id"]] = [dict(total, shared=shared) for total in _sum_rows(rows)]
    return out


# --------------------------------------------------------------------------- 3.3 six questions

QUESTIONS = ("Who holds investor capital?", "Who deploys credit?", "Who receives financing?", "Who must repay?",
             "Who can enforce the claim?", "Is deployment verified?")


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
    """[(question, answer), ...] for one strategy (six questions); `UNRESOLVED` for an empty answer."""
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

    index = doc["strategies"].index(strategy)
    deployment = strategy["deployment"]
    deployed = "" if deployment["status"] == "not_found" else "%s [%s]" % (
        plain_value(deployment["value"]), by_parts[("strategies", index, "deployment")])
    answers = [_join(ends("holder_L1", "to", "L1")), _join(deployers), _join(receivers), "; ".join(repay),
               enforce, deployed]
    return [(q, a or "UNRESOLVED") for q, a in zip(QUESTIONS, answers)]



# --------------------------------------------------------------------------- 3.5 section 1 selection

TYPE_ORDER = ("unreconciled_transaction", "discrepancy", "scope_unresolved", "gap", "structural_change")


def _group(finding):
    if finding["material"]:
        return 1
    if finding["blocking"] and finding["k_checks"]:
        return 2
    if finding["blocking"] and set(finding["impact"]) & set(schema.SECTION1_IMPACTS):
        return 3
    return None


def critical(doc):
    """Finding ids for report section 1 (curator Q10): material, then blocking with k_checks, then blocking with
    a section 1 impact; within a group by priority, type (R, D, U, G, C) and id. No cap."""
    picked = [(_group(f), f["priority"], TYPE_ORDER.index(f["type"]), id_key(f), f["id"])
              for f in doc["findings"] if _group(f) is not None]
    return [item[-1] for item in sorted(picked)]


def critical_counts(doc):
    """(selected, total findings, open findings not selected)."""
    selected = set(critical(doc))
    rest = sum(1 for f in doc["findings"] if f["id"] not in selected and f["resolution"]["status"] == "open")
    return len(selected), len(doc["findings"]), rest


# --------------------------------------------------------------------------- 3.6 resolve

RESOLVE_PATTERN = re.compile(r"^(@?(E|P|T|X|Z|G|D|C|U|R)[1-9][0-9]*)((\.[a-z][a-z0-9_]*)|(\[[0-9]+\]))*$")
_PART = re.compile(r"\.([a-z][a-z0-9_]*)|\[([0-9]+)\]")
_COLLECTIONS = {"E": ("entities",), "T": ("strategies",), "X": ("interfaces",), "Z": ("supports",),
                "P": ("project", "products")}


def _is_claim(node):
    return isinstance(node, dict) and set(node) == set(schema.CLAIM_KEYS)


def resolve(doc, path):
    """(kind, node) at a subject or expectation path, kind claim, object, list or scalar; KeyError when the path
    does not match the grammar or names nothing. `P<n>.holder_rights` is that product's holder_rights entry;
    `@<id>` is the finding carried from <id>, or the finding with that id when none carries from it."""
    match = RESOLVE_PATTERN.match(path) if isinstance(path, str) else None
    if match is None:
        raise KeyError(path)
    head = match.group(1)
    rest = path[len(head):]
    if head.startswith("@"):
        ident = head[1:]
        found = [f for f in doc["findings"] if f["carried_from"] == ident]
        found = found or [f for f in doc["findings"] if f["id"] == ident]
    elif head[0] in "GDCUR":
        found = [f for f in doc["findings"] if f["id"] == head]
    else:
        items = doc
        for key in _COLLECTIONS[head[0]]:
            items = items[key]
        found = [item for item in items if item["id"] == head]
    if not found:
        raise KeyError(path)
    node = found[0]
    parts = [(m.group(1), m.group(2)) for m in _PART.finditer(rest)]
    if head[0] == "P" and parts and parts[0][0] == "holder_rights":
        rights = [h for h in doc["holder_rights"] if h["product"] == head]
        if not rights:
            raise KeyError(path)
        node, parts = rights[0], parts[1:]
    for field, index in parts:
        if field is not None:
            if not isinstance(node, dict) or field not in node or _is_claim(node):
                raise KeyError(path)
            node = node[field]
        else:
            if not isinstance(node, list) or int(index) >= len(node):
                raise KeyError(path)
            node = node[int(index)]
    if _is_claim(node):
        return "claim", node
    if isinstance(node, dict):
        return "object", node
    if isinstance(node, list):
        return "list", node
    return "scalar", node
