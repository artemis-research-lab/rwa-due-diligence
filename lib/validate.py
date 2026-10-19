"""Whole-document validation: structure, references, id density, claim rules, ledger equality."""

import datetime
import re

from lib import claims, schema
from lib.textutil import has_control

LEDGER_MSG = "sources must be added with add-source"


# --------------------------------------------------------------------------- structure

def _join(path, key):
    return "%s.%s" % (path, key) if path else key


def _check_string(value, path, errors, max_len=None):
    if has_control(value):
        errors.append("%s: control character not allowed" % (path or "(root)"))
    if max_len is not None and len(value) > max_len:
        errors.append("%s: longer than %d characters" % (path, max_len))


def _check_any_json(value, path, errors):
    if isinstance(value, str):
        _check_string(value, path, errors, schema.CLAIM_VALUE_STR_MAX)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _check_any_json(item, "%s[%d]" % (path, i), errors)
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_string(key, path, errors)
            _check_any_json(item, _join(path, key), errors)


def _check_obj_keys(value, keys, path, errors):
    for key in keys:
        if key not in value:
            errors.append('%s: missing key "%s"' % (path or "(root)", key))
    for key in value:
        if key not in keys:
            errors.append('%s: unknown key "%s"' % (path or "(root)", key))


def _check_pattern(node, value, path, errors):
    if node.max_len is not None and len(value) > node.max_len:
        errors.append("%s: longer than %d characters" % (path, node.max_len))
        return
    if has_control(value) or not re.match(node.regex, value):
        errors.append("%s: must be %s" % (path, node.label))
        return
    try:
        if node.kind == "date":
            datetime.date.fromisoformat(value)
        elif node.kind == "timestamp":
            datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        errors.append("%s: not a real %s" % (path, node.kind))


def check_node(node, value, path, errors):
    if value is None:
        if not node.nullable:
            errors.append("%s: must not be null" % path)
        return
    if isinstance(node, schema.Claim):
        if not isinstance(value, dict):
            errors.append("%s: must be a Claim object" % path)
            return
        _check_obj_keys(value, schema.CLAIM_KEYS, path, errors)
        if "value" in value:
            _check_any_json(value["value"], _join(path, "value"), errors)
        if "status" in value:
            check_node(schema.Enum("claim_status"), value["status"], _join(path, "status"), errors)
        if "evidence" in value:
            check_node(schema.Arr(schema.Ref("S")), value["evidence"], _join(path, "evidence"), errors)
        if "subject" in value:
            check_node(schema.Ref("E", "P", nullable=True), value["subject"], _join(path, "subject"), errors)
        if "note" in value:
            check_node(schema.Str(schema.CLAIM_NOTE_MAX), value["note"], _join(path, "note"), errors)
    elif isinstance(node, schema.Obj):
        if not isinstance(value, dict):
            errors.append("%s: must be an object" % (path or "(root)"))
            return
        _check_obj_keys(value, node.keys(), path, errors)
        for name, child in node.fields:
            if name in value:
                check_node(child, value[name], _join(path, name), errors)
    elif isinstance(node, schema.Arr):
        if not isinstance(value, list):
            errors.append("%s: must be an array" % path)
            return
        if len(value) < node.min_items:
            errors.append("%s: needs at least %d item(s)" % (path, node.min_items))
        for i, item in enumerate(value):
            check_node(node.item, item, "%s[%d]" % (path, i), errors)
    elif isinstance(node, schema.Const):
        if value != node.value:
            errors.append('%s: must be "%s"' % (path, node.value))
    elif isinstance(node, schema.Enum):
        if not isinstance(value, str) or value not in schema.ENUMS[node.name]:
            errors.append("%s: not a valid %s" % (path, node.name))
    elif isinstance(node, schema.Bool):
        if not isinstance(value, bool):
            errors.append("%s: must be a boolean" % path)
    elif isinstance(node, schema.Int):
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append("%s: must be an integer" % path)
        elif (value < node.minimum) or (node.maximum is not None and value > node.maximum):
            errors.append("%s: out of range (%s)" % (path, node.describe()))
    elif isinstance(node, schema.Str):
        if not isinstance(value, str):
            errors.append("%s: must be a string" % path)
            return
        _check_string(value, path, errors, node.max_len)
    elif isinstance(node, schema.Pattern):
        if not isinstance(value, str):
            errors.append("%s: must be a string" % path)
            return
        _check_pattern(node, value, path, errors)
    else:  # pragma: no cover - schema programming error
        raise TypeError("unknown schema node %r" % node)


def structural_errors(doc, node=schema.DOCUMENT):
    errors = []
    check_node(node, doc, "", errors)
    return errors


# --------------------------------------------------------------------------- semantics

def _id_num(ident):
    return int(ident[1:])


def _check_ids(items, prefix, path, errors):
    seen = set()
    for i, item in enumerate(items):
        ident = item["id"]
        if ident in seen:
            errors.append("%s[%d].id: duplicate id %s" % (path, i, ident))
        seen.add(ident)
    nums = sorted(_id_num(x) for x in seen)
    if nums != list(range(1, len(nums) + 1)):
        errors.append("%s: %s ids must be dense from %s1" % (path, prefix, prefix))


def _need(ident, known, path, errors, what):
    if ident is not None and ident not in known:
        errors.append("%s: unknown %s %s" % (path, what, ident))


def _coded_errors(path, value, enum, shape):
    """Errors for one coded claim value (D39); value is not None."""
    if shape == "one":
        if not isinstance(value, str) or value not in schema.ENUMS[enum]:
            return ["%s: value must be one of %s" % (path, enum)]
    elif shape == "list":
        if (not isinstance(value, list) or not value or len(set(map(repr, value))) != len(value)
                or any(not isinstance(v, str) or v not in schema.ENUMS[enum] for v in value)):
            return ["%s: value must be a non-empty list of %s" % (path, enum)]
    elif not isinstance(value, list) or not value or any(not isinstance(v, str) for v in value):
        return ["%s: value must be a non-empty list of strings" % path]
    return []


def _framework_errors(doc, ids, errors):
    """Rules of schema rwa-dd/2.0: strategies, functions, interfaces, holder rights, flow edges, subjects."""
    sids, eids, pids, tids, xids = ids["S"], ids["E"], ids["P"], ids["T"], ids["X"]
    strategies = doc["strategies"]
    interfaces = doc["interfaces"]

    for i, t in enumerate(strategies):
        for j, p in enumerate(t["products"]):
            _need(p, pids, "strategies[%d].products[%d]" % (i, j), errors, "product")
    for i, e in enumerate(doc["entities"]):
        for j, fn in enumerate(e["functions"]):
            _need(fn["strategy"], tids, "entities[%d].functions[%d].strategy" % (i, j), errors, "strategy")
            for k, sid in enumerate(fn["evidence"]):
                _need(sid, sids, "entities[%d].functions[%d].evidence[%d]" % (i, j, k), errors, "source")
    for i, x in enumerate(interfaces):
        path = "interfaces[%d]" % i
        _need(x["strategy"], tids, path + ".strategy", errors, "strategy")
        _need(x["from"], eids | pids, path + ".from", errors, "entity/product")
        _need(x["to"], eids, path + ".to", errors, "entity")
        if x["from"] == x["to"]:
            errors.append("interfaces[%d]: from and to must differ (%s)" % (i, x["from"]))
        holder = x["kind"] == "holder_L1"
        if holder and x["from"][0] != "P":
            errors.append("%s.from: kind holder_L1 requires a product id" % path)
        if not holder and x["from"][0] == "P":
            errors.append("%s.from: a product id is allowed only for kind holder_L1" % path)
        for field, kind in (("route", "L1_L2"), ("method", "L2_L3")):
            claim = x[field]
            if x["kind"] != kind and (claim["status"] != "not_found" or claim["evidence"]):
                errors.append("%s.%s: must be not_found without evidence unless kind is %s" % (path, field, kind))
    for i, h in enumerate(doc["holder_rights"]):
        _need(h["product"], pids, "holder_rights[%d].product" % i, errors, "product")
    for i, e in enumerate(doc["flows"]["edges"]):
        for j, t in enumerate(e["strategies"]):
            _need(t, tids, "flows.edges[%d].strategies[%d]" % (i, j), errors, "strategy")
        _need(e["interface"], xids, "flows.edges[%d].interface" % i, errors, "interface")
    known = {"E": eids, "P": pids, "T": tids, "X": xids}
    for i, f in enumerate(doc["findings"]):
        for j, subject in enumerate(f["subjects"]):
            lead = subject.split(".", 1)[0]
            _need(lead, known[lead[0]], "findings[%d].subjects[%d]" % (i, j), errors, "id")

    for parts, claim in schema.iter_claims(doc):
        coded = schema.CODED_CLAIMS.get((parts[0], parts[-1]))
        if coded is not None and claim["value"] is not None:
            errors.extend(_coded_errors(schema.format_path(parts), claim["value"], *coded))

    in_strategy = {p for t in strategies for p in t["products"]}
    yield_products = {y["product"] for y in doc["yield"]}
    for i, p in enumerate(doc["project"]["products"]):
        pid = p["id"]
        if pid not in in_strategy:
            errors.append("project.products[%d]: %s is in no strategy" % (i, pid))
        rights = sum(1 for h in doc["holder_rights"] if h["product"] == pid)
        if rights != 1:
            errors.append("project.products[%d]: %s needs exactly one holder_rights entry (found %d)"
                          % (i, pid, rights))
        if pid not in yield_products:
            errors.append("project.products[%d]: %s has no yield entry" % (i, pid))
    settled = {t for e in doc["flows"]["edges"] if e["view"] == "settlement" for t in e["strategies"]}
    for i, t in enumerate(strategies):
        if t["id"] not in settled:
            errors.append("strategies[%d]: %s has no flow edge with view settlement" % (i, t["id"]))


def semantic_errors(doc):
    errors = []
    products = doc["project"]["products"]
    entities = doc["entities"]
    sources = doc["sources"]
    nodes = doc["flows"]["nodes"]
    findings = doc["findings"]
    searches = doc["next_searches"]

    _check_ids(sources, "S", "sources", errors)
    _check_ids(entities, "E", "entities", errors)
    _check_ids(products, "P", "project.products", errors)
    _check_ids(doc["strategies"], "T", "strategies", errors)
    _check_ids(doc["interfaces"], "X", "interfaces", errors)
    _check_ids(nodes, "n", "flows.nodes", errors)
    _check_ids(searches, "N", "next_searches", errors)
    _check_ids(doc["issuer_requests"], "Q", "issuer_requests", errors)
    for prefix in ("G", "D", "C"):
        _check_ids([f for f in findings if f["id"][0] == prefix], prefix, "findings", errors)

    sids = {s["id"] for s in sources}
    eids = {e["id"] for e in entities}
    pids = {p["id"] for p in products}
    nids = {n["id"] for n in nodes}
    fids = {f["id"] for f in findings}
    ids = {"S": sids, "E": eids, "P": pids, "T": {t["id"] for t in doc["strategies"]},
           "X": {x["id"] for x in doc["interfaces"]}}

    for i, s in enumerate(sources):
        _need(s["publisher"], eids, "sources[%d].publisher" % i, errors, "entity")
    for section in ("yield", "redemption", "eligibility", "size"):
        for i, item in enumerate(doc[section]):
            _need(item["product"], pids, "%s[%d].product" % (section, i), errors, "product")
    for i, a in enumerate(doc["audits"]):
        _need(a["report_ref"], sids, "audits[%d].report_ref" % i, errors, "source")
    for i, n in enumerate(nodes):
        ref = n["ref"]
        if ref is not None and re.match(r"^(E|P)[0-9]+$", ref):
            _need(ref, eids | pids, "flows.nodes[%d].ref" % i, errors, "entity/product")
    for i, e in enumerate(doc["flows"]["edges"]):
        _need(e["from"], nids, "flows.edges[%d].from" % i, errors, "node")
        _need(e["to"], nids, "flows.edges[%d].to" % i, errors, "node")
    for section in ("history", "findings", "x_unmapped"):
        for i, item in enumerate(doc[section]):
            for j, sid in enumerate(item["evidence"]):
                _need(sid, sids, "%s[%d].evidence[%d]" % (section, i, j), errors, "source")
    for i, f in enumerate(findings):
        if f["id"][0] != schema.FINDING_PREFIX[f["type"]]:
            errors.append("findings[%d].id: prefix of %s does not match type %s" % (i, f["id"], f["type"]))
    for i, n in enumerate(searches):
        for j, fid in enumerate(n["resolves"]):
            _need(fid, fids, "next_searches[%d].resolves[%d]" % (i, j), errors, "finding")

    _framework_errors(doc, ids, errors)

    keys = [(h["date"] is None, h["date"] or "") for h in doc["history"]]
    if keys != sorted(keys):
        errors.append("history: must be sorted by date (nulls last)")

    run = doc["run"]
    if (run["status"] == "final") != (run["finalized_at"] is not None):
        errors.append("run.finalized_at: must be set exactly when status is final")

    errors.extend(claims.check_all(doc))
    return errors


def ledger_errors(doc_sources, ledger):
    if len(doc_sources) != len(ledger):
        return ["sources: %d entries but the ledger has %d (%s)" % (len(doc_sources), len(ledger), LEDGER_MSG)]
    return ["sources[%d]: differs from ledger entry %d (%s)" % (i, i + 1, LEDGER_MSG)
            for i, (a, b) in enumerate(zip(doc_sources, ledger)) if a != b]


def validate_document(doc, ledger=None):
    """Return the sorted list of errors; empty means valid. ledger=None skips the ledger check."""
    errors = structural_errors(doc)
    if not errors:
        errors = semantic_errors(doc)
        if ledger is not None:
            errors.extend(ledger_errors(doc["sources"], ledger))
    return sorted(set(errors))
