"""Conversion of an rwa-dd/1.0 record into rwa-dd/2.0 (D38, D42); pure, invents no classification.

Everything the earlier schema held but the new one cannot place (entity roles, relationships) is kept as an
x_unmapped fact so the agent can re-map it.
"""

import copy
import json

from lib import schema
from lib.textutil import clip, id_key

FROM_VERSION = "rwa-dd/1.0"
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
    name = product["name"]["value"]
    strategy.update({"id": "T" + k, "products": [product["id"]],
                     "name": clip(name, 80) if isinstance(name, str) else "Strategy for P" + k})
    if loss is not None:
        strategy["default_path"]["loss_waterfall"] = _waterfall(loss)
    return strategy


def convert(old, run):
    """rwa-dd/2.0 document from the rwa-dd/1.0 document old; run is the complete new run block."""
    doc = {"schema_version": schema.SCHEMA_VERSION, "run": copy.deepcopy(run)}
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
