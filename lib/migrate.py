"""Conversion of earlier records into the current schema (D38, D42, D52); pure, invents no classification.

convert: rwa-dd/1.0 -> 2.0. Everything 1.0 held but 2.0 cannot place (entity roles, relationships) is kept as
an x_unmapped fact so the agent can re-map it.
convert_20: rwa-dd/2.0 -> 2.1. New fields get their weakest reading and visible placeholders.
convert_21: rwa-dd/2.1 -> 2.2 (v0.7.0 4.1). Amounts become typed entries with a placeholder scope, findings get
their 2.2 fields with placeholder scope notes; finalize refuses the placeholders until they are re-checked.
convert and convert_20 still emit their own versions: their output is ordered by the frozen 2.1 layout.
"""

import copy
import json

from lib import schema
from lib.textutil import clip, has_control, id_key

FROM_VERSION = "rwa-dd/1.0"
V20 = "rwa-dd/2.0"
V21 = "rwa-dd/2.1"
SEEDABLE = (FROM_VERSION, V20, V21, schema.SCHEMA_VERSION)
CLAIM_KEYS_21 = ("value", "status", "evidence", "subject", "note")
# 2.0 interface claims added by 2.1, in schema order.
NEW_INTERFACE_CLAIMS = ("amount", "supply_concentration", "title_transfer", "servicing", "residual_exposure")
COPIED = ("project", "sources", "audits", "size", "redemption", "eligibility", "onchain", "history",
          "open_questions", "narrative")
ROLES_WHY = "assign layers in functions"
RELATIONSHIP_WHY = "rwa-dd/1.0 relationship; re-map into interfaces"


def _text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)


# --------------------------------------------------------------------------- frozen rwa-dd/2.1 layout

def _swap(obj, replace=None, drop=(), add_after=None):
    """Copy of Obj obj with fields replaced, dropped or inserted after another field."""
    replace = replace or {}
    add_after = add_after or {}
    fields = []
    for name, child in obj.fields:
        if name in drop:
            continue
        for new_name, new_child in replace.get(name, [(name, child)]):
            fields.append((new_name, new_child))
        fields += add_after.get(name, [])
    return schema.Obj(*fields)


_C = schema.C
_FIELDS = dict(schema.DOCUMENT.fields)
_FINDING_21 = schema.Obj(*[(n, c) for n, c in _FIELDS["findings"].item.fields
                           if n in ("id", "type", "topic", "blocking", "material", "statement", "scope_note",
                                    "evidence", "subjects")])
DOCUMENT_21 = _swap(schema.DOCUMENT, replace={
    "strategies": [("strategies", schema.Arr(_swap(schema.STRATEGY, drop=("deployment",)), min_items=1))],
    "interfaces": [("interfaces", schema.Arr(_swap(schema.INTERFACE, replace={
        "amounts": [("amount", _C), ("amount_basis", schema.Enum("amount_basis", nullable=True))],
        "supply_concentration": [("supply_concentration", _C)]},
        drop=("loan_identity", "seller_of_record", "buyer_of_record", "repayment_source"))))],
    "findings": [("findings", schema.Arr(_FINDING_21))],
})


def _claims_21(value):
    """value with every 2.2 claim reduced to the five 2.1 claim keys."""
    if isinstance(value, dict):
        if set(value) == set(schema.CLAIM_KEYS):
            return {k: value[k] for k in CLAIM_KEYS_21}
        return {k: _claims_21(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_claims_21(v) for v in value]
    return value


def _order_21(doc):
    """doc ordered by the rwa-dd/2.1 layout (claims keep their own key order)."""
    def walk(value, node):
        if isinstance(node, schema.Claim) and isinstance(value, dict):
            known = [k for k in CLAIM_KEYS_21 if k in value]
            return {k: value[k] for k in known + [k for k in value if k not in CLAIM_KEYS_21]}
        if isinstance(node, schema.Obj) and isinstance(value, dict):
            children = dict(node.fields)
            out = {name: walk(value[name], children[name]) for name in node.keys() if name in value}
            out.update((name, value[name]) for name in value if name not in children)
            return out
        if isinstance(node, schema.Arr) and isinstance(value, list):
            return [walk(item, node.item) for item in value]
        return value
    return walk(doc, DOCUMENT_21)


def _empty_claim_21():
    return _claims_21(schema.empty_claim())


def _waterfall(claim):
    claim = copy.deepcopy(claim)
    if isinstance(claim["value"], str):
        claim["value"] = [claim["value"]]
    return claim


def _strategy(product, loss):
    k = product["id"][1:]
    strategy = _claims_21(schema.skeleton(schema.STRATEGY))
    del strategy["component"]  # a 2.0 strategy has no component
    del strategy["deployment"]
    name = product["name"]["value"]
    strategy.update({"id": "T" + k, "products": [product["id"]],
                     "name": clip(name, 80) if isinstance(name, str) else "Strategy for P" + k})
    if loss is not None:
        strategy["default_path"]["loss_waterfall"] = _waterfall(loss)
    return strategy


def convert(old, run):
    """rwa-dd/2.0 document from the rwa-dd/1.0 document old; run is the complete new run block."""
    doc = {"schema_version": V20, "run": copy.deepcopy(run)}
    for key in COPIED:
        doc[key] = copy.deepcopy(old[key])

    products = sorted(old["project"]["products"], key=id_key)
    loss = {}
    for y in old["yield"]:
        loss.setdefault(y["product"], y["loss_absorption"])
    doc["strategies"] = [_strategy(p, loss.get(p["id"])) for p in products]

    doc["yield"] = [{k: copy.deepcopy(v) for k, v in y.items() if k != "loss_absorption"} for y in old["yield"]]

    unmapped = copy.deepcopy(old["x_unmapped"])
    doc["entities"] = []
    for e in old["entities"]:
        entity = {k: copy.deepcopy(v) for k, v in e.items() if k != "roles"}
        entity["functions"] = []
        doc["entities"].append(entity)
        unmapped.append({"fact": clip("%s roles in rwa-dd/1.0: %s" % (e["id"], ", ".join(e["roles"])), 200),
                         "evidence": [], "why_unmapped": ROLES_WHY})
    for r in old["relationships"]:
        fact = "%s %s %s: %s" % (r["from"], r["type"], r["to"], _text(r["claim"]["value"]))
        unmapped.append({"fact": clip(fact, 200), "evidence": list(r["claim"]["evidence"]),
                         "why_unmapped": RELATIONSHIP_WHY})

    doc["interfaces"] = []
    doc["holder_rights"] = []
    for p in products:
        rights = _claims_21(schema.skeleton(schema.HOLDER_RIGHTS))
        rights["product"] = p["id"]
        rights["governing_law"] = copy.deepcopy(old["governing_law"])
        doc["holder_rights"].append(rights)

    flows = copy.deepcopy(old["flows"])
    for node in flows["nodes"]:
        node["layer"] = None
    for edge in flows["edges"]:
        edge["view"] = "settlement"
        edge["strategies"] = ["T" + p[1:] for p in sorted(edge.pop("products"), key=id_key)]
        edge["interface"] = None
    doc["flows"] = flows

    doc["findings"] = [dict(copy.deepcopy(f), subjects=[]) for f in old["findings"]]
    doc["next_searches"] = []
    doc["issuer_requests"] = []
    doc["x_unmapped"] = unmapped
    return _order_21(doc)


def _obligor(entity, strategy_id):
    return entity is not None and any(
        fn["role"] == "ultimate_obligor" and fn["strategy"] in (strategy_id, None) for fn in entity["functions"])


def convert_20(old, run):
    """rwa-dd/2.1 document from the rwa-dd/2.0 document old; run is the complete new run block."""
    doc = copy.deepcopy(old)
    doc["schema_version"] = V21
    doc["run"] = copy.deepcopy(run)
    doc["next_searches"] = []
    for t in doc["strategies"]:
        t["component"] = "CORE_CREDIT"
    entities = {e["id"]: e for e in old["entities"]}
    for e in doc["entities"]:
        e["entity_class"] = "unknown"
        for fn in e["functions"]:
            if fn["role"] == "ultimate_obligor":
                fn["layer"] = "L3-O"
                fn["role"] = "cash_flow_source"
    for x in doc["interfaces"]:
        if x["kind"] == "within_L3" and _obligor(entities.get(x["to"]), x["strategy"]):
            x["kind"] = "L3_L3O"
        x["alternative"] = {"group": None, "option": None}
        for field in NEW_INTERFACE_CLAIMS:
            x[field] = _empty_claim_21()
        x["amount_basis"] = None
    doc["supports"] = []
    for f in doc["findings"]:
        f["material"] = False
        f["scope_note"] = schema.MIGRATED_SCOPE_NOTE if f["type"] == "discrepancy" else ""
    return _order_21(doc)


# --------------------------------------------------------------------------- rwa-dd/2.1 -> 2.2

# 2.1 amount_basis -> 2.2 amount basis (None: an amount without a basis).
BASIS_MAP = {"GROSS_FUNDED": "OTHER", "COMMITMENT": "FACILITY_COMMITMENT", "LOOKTHROUGH": "RESERVE_LOOKTHROUGH",
             "RESERVE": "RESERVE_LOOKTHROUGH", "SALE_PROCEEDS": "SALE_PROCEEDS", None: "OTHER"}
SALE_CLAIMS_22 = ("loan_identity", "seller_of_record", "buyer_of_record", "repayment_source")
UNIT_MAX = 20
NO_UNIT = "n/d"


def _claims_22(value):
    """value with origin and assurance (null) added to every 2.1 claim."""
    if isinstance(value, dict):
        if set(value) == set(CLAIM_KEYS_21):
            return dict(value, origin=None, assurance=None)
        return {k: _claims_22(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_claims_22(v) for v in value]
    return value


def _unit(currency):
    """A 2.1 currency value as a 2.2 amount unit: the string when it fits, else `n/d` (the currency claim
    itself is kept on the interface)."""
    value = currency["value"]
    if isinstance(value, str) and value.strip() and len(value) <= UNIT_MAX and not has_control(value):
        return value
    return NO_UNIT


def _amounts(x):
    claim = x["amount"]
    if claim["value"] is None:
        return []
    value = dict(claim)
    basis = x["amount_basis"]
    if not value["note"]:
        value["note"] = "2.1 basis %s" % ("null" if basis is None else basis)
    return [{"basis": BASIS_MAP[basis], "value": value, "unit": _unit(x["currency"]), "as_of": None,
             "block": None, "chain": None, "scope": schema.MIGRATED_AMOUNT_SCOPE, "valuation_basis": None}]


def _supply(claim):
    ratio = schema.empty_claim()
    if claim["value"] is not None or claim["evidence"]:
        text = "" if claim["value"] is None else _text(claim["value"])
        ratio.update({"evidence": list(claim["evidence"]), "note": clip("migrated: " + text, schema.CLAIM_NOTE_MAX)})
    return {"ratio": ratio, "numerator": "", "denominator": "", "as_of": None, "block": None, "chain": None}


def _scope_note_21(note):
    if note and not schema.is_placeholder(note):
        return clip("%s -- %s" % (schema.MIGRATED_NOTE_21, note), 200)
    return schema.MIGRATED_NOTE_21


def _subject_21(subject, interfaces):
    """A 2.1 subject renamed to its 2.2 path: X<n>.amount -> X<n>.amounts[0].value (X<n> when no amount was
    carried over), X<n>.supply_concentration -> X<n>.supply_concentration.ratio."""
    head, _, rest = subject.partition(".")
    if head[:1] != "X" or head not in interfaces:
        return subject
    if rest == "amount":
        return head + ".amounts[0].value" if interfaces[head]["amounts"] else head
    if rest == "supply_concentration":
        return subject + ".ratio"
    return subject


def convert_21(old, run):
    """rwa-dd/2.2 document from the rwa-dd/2.1 document old; run is the complete new run block."""
    doc = _claims_22(copy.deepcopy(old))
    doc["schema_version"] = schema.SCHEMA_VERSION
    doc["run"] = copy.deepcopy(run)
    doc["next_searches"] = []
    for t in doc["strategies"]:
        t["deployment"] = schema.empty_claim()
    for x in doc["interfaces"]:
        x["amounts"] = _amounts(x)
        del x["amount"], x["amount_basis"]
        x["supply_concentration"] = _supply(x["supply_concentration"])
        for field in SALE_CLAIMS_22:
            x[field] = schema.empty_claim()
    interfaces = {x["id"]: x for x in doc["interfaces"]}
    for f in doc["findings"]:
        kind = f["type"]
        if kind in ("discrepancy", "scope_unresolved"):
            f["scope_note"] = _scope_note_21(f["scope_note"])
        f["scope_match"] = "unchecked" if kind in ("discrepancy", "scope_unresolved") else "not_applicable"
        f["subjects"] = [_subject_21(s, interfaces) for s in f["subjects"]]
        f["assertions"] = []
        f["resolution"] = {"status": "not_applicable" if kind == "structural_change" else "open", "note": ""}
        f["k_checks"] = []
        f["impact"] = []
        f["priority"] = 2
        f["carried_from"] = f["id"]
    return schema.order_like_schema(doc)


def migrate_to_current(old, run):
    """Current-schema document from a seedable record: 1.0 via convert, convert_20 and convert_21; 2.0 via
    convert_20 and convert_21; 2.1 via convert_21; 2.2 as a copy with run reset and next_searches emptied (run
    applied once in every chain)."""
    version = old.get("schema_version")
    if version == FROM_VERSION:
        return convert_21(convert_20(convert(old, run), run), run)
    if version == V20:
        return convert_21(convert_20(old, run), run)
    if version == V21:
        return convert_21(old, run)
    if version == schema.SCHEMA_VERSION:
        return schema.order_like_schema(dict(copy.deepcopy(old), run=copy.deepcopy(run), next_searches=[]))
    raise ValueError("cannot migrate schema version %r" % (version,))
