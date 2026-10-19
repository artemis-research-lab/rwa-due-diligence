"""Conversion of earlier records into the current schema (D38, D42, D52); pure, invents no classification.

convert: rwa-dd/1.0 -> 2.0. Everything 1.0 held but 2.0 cannot place (entity roles, relationships) is kept as
an x_unmapped fact so the agent can re-map it.
convert_20: rwa-dd/2.0 -> 2.1. New fields get their weakest reading and visible placeholders.
"""

import copy
import json

from lib import schema
from lib.textutil import clip, id_key

FROM_VERSION = "rwa-dd/1.0"
V20 = "rwa-dd/2.0"
SEEDABLE = (FROM_VERSION, V20, schema.SCHEMA_VERSION)
# 2.0 interface claims added by 2.1, in schema order.
NEW_INTERFACE_CLAIMS = ("amount", "supply_concentration", "title_transfer", "servicing", "residual_exposure")
COPIED = ("project", "sources", "audits", "size", "redemption", "eligibility", "onchain", "history",
          "open_questions", "narrative")
ROLES_WHY = "assign layers in functions"
RELATIONSHIP_WHY = "rwa-dd/1.0 relationship; re-map into interfaces"


def _text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)


def _waterfall(claim):
    claim = copy.deepcopy(claim)
    if isinstance(claim["value"], str):
        claim["value"] = [claim["value"]]
    return claim


def _strategy(product, loss):
    k = product["id"][1:]
    strategy = schema.skeleton(schema.STRATEGY)
    del strategy["component"]  # a 2.0 strategy has no component
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
        rights = schema.skeleton(schema.HOLDER_RIGHTS)
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
    return schema.order_like_schema(doc)


def _obligor(entity, strategy_id):
    return entity is not None and any(
        fn["role"] == "ultimate_obligor" and fn["strategy"] in (strategy_id, None) for fn in entity["functions"])


def convert_20(old, run):
    """rwa-dd/2.1 document from the rwa-dd/2.0 document old; run is the complete new run block."""
    doc = copy.deepcopy(old)
    doc["schema_version"] = schema.SCHEMA_VERSION
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
            x[field] = schema.empty_claim()
        x["amount_basis"] = None
    doc["supports"] = []
    for f in doc["findings"]:
        f["material"] = False
        f["scope_note"] = schema.MIGRATED_SCOPE_NOTE if f["type"] == "discrepancy" else ""
    return schema.order_like_schema(doc)


def migrate_to_current(old, run):
    """Current-schema document from a seedable record: 1.0 via convert then convert_20 (run applied once),
    2.0 via convert_20, 2.1 as a copy with run reset and next_searches emptied."""
    version = old.get("schema_version")
    if version == FROM_VERSION:
        return convert_20(convert(old, run), run)
    if version == V20:
        return convert_20(old, run)
    if version == schema.SCHEMA_VERSION:
        return schema.order_like_schema(dict(copy.deepcopy(old), run=copy.deepcopy(run), next_searches=[]))
    raise ValueError("cannot migrate schema version %r" % (version,))
