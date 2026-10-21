"""Whole-document validation: structure, references, id density, claim rules, ledger equality."""

import datetime
import re

from lib import claims, framework, schema
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
        elif node.kind == "date_or_timestamp":
            if len(value) > 10:
                datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            else:
                datetime.date.fromisoformat(value)
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
        if "origin" in value:
            check_node(schema.Enum("assertion_origin", nullable=True), value["origin"], _join(path, "origin"),
                       errors)
        if "assurance" in value:
            check_node(schema.Enum("assurance_scope", nullable=True), value["assurance"],
                       _join(path, "assurance"), errors)
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
    elif shape == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            return ["%s: value must be a number >= 0" % path]
    elif shape == "ratio":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            return ["%s: value must be a number 0..1" % path]
    elif not isinstance(value, list) or not value or any(not isinstance(v, str) for v in value):
        return ["%s: value must be a non-empty list of strings" % path]
    return []


# Kind constraints (v0.6.0 2.2, v0.7.0 2.2): claim field -> kinds where it may hold a value or evidence.
KIND_FIELDS = (
    ("route", ("L1_L2",)),
    ("method", ("L2_L3", "L3_L3O")),
    ("title_transfer", ("asset_sale",)),
    ("servicing", ("asset_sale",)),
    ("residual_exposure", ("asset_sale",)),
    ("loan_identity", ("asset_sale",)),
    ("seller_of_record", ("asset_sale",)),
    ("buyer_of_record", ("asset_sale",)),
    ("repayment_source", ("asset_sale",)),
)

# Amounts (v0.7.0 2.2): kinds that may carry amounts, and bases limited to some kinds.
AMOUNT_KINDS = ("L1_L2", "L2_L3", "within_L1", "within_L2", "sleeve_holding", "reserve_lookthrough", "asset_sale")
BASIS_KINDS = {
    "RESERVE_LOOKTHROUGH": ("reserve_lookthrough",),
    "SALE_PROCEEDS": ("asset_sale",),
    "FACILITY_COMMITMENT": ("L1_L2", "L2_L3", "within_L2"),
    "UNDRAWN_COMMITMENT": ("L1_L2", "L2_L3", "within_L2"),
}
OTHER_SCOPE_MIN = 20

# Strategy components that carry a deployment claim.
DEPLOYMENT_COMPONENTS = ("CORE_CREDIT", "DEFI_LENDING")

# Findings (v0.7.0 2.2): allowed scope_match and resolution status per type.
SCOPE_MATCH = {
    "gap": ("not_applicable",),
    "structural_change": ("not_applicable",),
    "discrepancy": ("matched",),
    "scope_unresolved": ("not_matched", "unchecked"),
    "unreconciled_transaction": ("matched", "not_matched", "unchecked"),
}
RESOLUTION = {
    "gap": ("open", "resolved"),
    "discrepancy": ("open", "resolved"),
    "scope_unresolved": ("open", "resolved"),
    "unreconciled_transaction": ("open", "resolved"),
    "structural_change": ("not_applicable",),
}
ASSERTED_TYPES = ("discrepancy", "scope_unresolved", "unreconciled_transaction")

# Roles whose function may have a null layer.
LAYERLESS_ROLES = ("issuer", "loan_purchaser", "protection_provider", "reserve_assets", "auditor", "other")

# Components that need a settlement flow edge.
SETTLED_COMPONENTS = ("CORE_CREDIT", "DEFI_LENDING")


def _alternative_errors(interfaces, errors):
    groups = {}
    for i, x in enumerate(interfaces):
        alt = x["alternative"]
        if (alt["group"] is None) != (alt["option"] is None):
            errors.append("interfaces[%d].alternative: group and option must both be set or both null" % i)
        elif alt["group"] is not None:
            groups.setdefault(alt["group"], []).append(x)
    for group, members in groups.items():
        if len({x["alternative"]["option"] for x in members}) < 2:
            errors.append("alternative group %s needs at least two options" % group)
        if len({x["strategy"] for x in members}) > 1:
            errors.append("alternative group %s spans strategies" % group)


def _amount_errors(doc, x, path, errors):
    kind = x["kind"]
    if x["amounts"] and kind not in AMOUNT_KINDS:
        errors.append("%s.amounts: not allowed on %s" % (path, kind))
    for j, a in enumerate(x["amounts"]):
        where = "%s.amounts[%d]" % (path, j)
        if a["value"]["status"] == "not_found":
            errors.append("%s.value: an amount entry needs a value; remove the entry instead" % where)
        if not a["unit"].strip():
            errors.append("%s.unit: required" % where)
        if not a["scope"].strip():
            errors.append("%s.scope: required" % where)
        elif a["basis"] == "OTHER" and len(a["scope"].strip()) < OTHER_SCOPE_MIN:
            errors.append("%s.scope: OTHER needs an explicit definition (>= %d characters)" % (where, OTHER_SCOPE_MIN))
        if a["basis"] == "POSITION_VALUE" and not (a["valuation_basis"] or "").strip():
            errors.append("%s.valuation_basis: required for POSITION_VALUE" % where)
        if a["block"] is not None and a["chain"] is None:
            errors.append("%s.chain: required when block is set" % where)
        if a["block"] is not None and (a["as_of"] is None or len(a["as_of"]) != len("YYYY-MM-DDTHH:MM:SSZ")):
            errors.append("%s.as_of: a block read needs the block timestamp (curator AC-03)" % where)
        retrieved = framework.retrieval_source(doc, a)
        if retrieved is not None:
            errors.append("%s.as_of: equals the retrieval time of %s; record the time the source gives for the value,"
                          " or null (curator AC-03)" % (where, retrieved))
        kinds = BASIS_KINDS.get(a["basis"])
        if kinds is not None and kind not in kinds:
            errors.append("%s.basis: %s not allowed on %s" % (where, a["basis"], kind))


def _supply_errors(x, path, errors):
    sc = x["supply_concentration"]
    ratio = sc["ratio"]
    empty = (ratio["status"] == "not_found" and not ratio["evidence"] and not sc["numerator"]
             and not sc["denominator"] and sc["as_of"] is None and sc["block"] is None and sc["chain"] is None)
    if x["kind"] != "L1_L2" and not empty:
        errors.append("%s.supply_concentration: must be not_found without evidence unless kind is L1_L2" % path)
    if ratio["value"] is not None and (not sc["numerator"].strip() or not sc["denominator"].strip()
                                       or sc["as_of"] is None):
        errors.append("%s.supply_concentration: numerator, denominator and as_of are required with a ratio" % path)


def _unique(values):
    return len(set(values)) == len(values)


def _finding_errors(doc, known, errors):
    carried = {}
    for i, f in enumerate(doc["findings"]):
        path = "findings[%d]" % i
        kind = f["type"]
        placeholder = schema.is_placeholder(f["scope_note"])
        allowed = SCOPE_MATCH[kind]
        if kind == "discrepancy" and placeholder:
            allowed = ("matched", "unchecked")
        if f["scope_match"] not in allowed:
            errors.append("%s.scope_match: %s not allowed for %s" % (path, f["scope_match"], kind))
        if kind in ASSERTED_TYPES:
            if not f["scope_note"].strip():
                errors.append("%s.scope_note: required for a %s" % (path, kind))
            if not placeholder and len(f["assertions"]) < 2:
                errors.append("%s.assertions: at least two statements required for %s" % (path, kind))
        elif f["assertions"]:
            errors.append("%s.assertions: must be empty for %s" % (path, kind))
        for j, a in enumerate(f["assertions"]):
            if a["source"] not in f["evidence"]:
                errors.append("%s.assertions[%d].source: not in evidence" % (path, j))
        if kind == "discrepancy" and not f["subjects"] and not placeholder:
            errors.append("%s.subjects: at least one claim required for a discrepancy" % path)
        for j, subject in enumerate(f["subjects"]):
            where = "%s.subjects[%d]" % (path, j)
            lead = subject.split(".", 1)[0]
            if lead not in known[lead[0]]:
                _need(lead, known[lead[0]], where, errors, "id")
                continue
            try:
                found, _ = framework.resolve(doc, subject)
            except KeyError:
                errors.append("%s: %s does not resolve" % (where, subject))
                continue
            if kind == "discrepancy" and found != "claim":
                errors.append("%s: %s is not a claim" % (where, subject))
            elif found not in ("claim", "object"):
                errors.append("%s: %s is not a claim or object" % (where, subject))
        status = f["resolution"]["status"]
        if status not in RESOLUTION[kind]:
            errors.append("%s.resolution.status: %s not allowed for %s" % (path, status, kind))
        if status == "resolved" and not f["resolution"]["note"].strip():
            errors.append("%s.resolution.note: required when resolved" % path)
        if not _unique(f["k_checks"]):
            errors.append("%s.k_checks: duplicate value" % path)
        if not _unique(f["impact"]):
            errors.append("%s.impact: duplicate value" % path)
        if f["carried_from"] is not None:
            if f["carried_from"] in carried:
                errors.append("%s.carried_from: %s already carried by %s"
                              % (path, f["carried_from"], carried[f["carried_from"]]))
            carried.setdefault(f["carried_from"], f["id"])


def _framework_errors(doc, ids, errors):
    """Rules of schema rwa-dd/2.2: strategies, functions, interfaces, amounts, supports, holder rights, flow
    edges, subjects, findings."""
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
            if fn["layer"] is None and fn["role"] not in LAYERLESS_ROLES:
                errors.append("entities[%d].functions[%d].layer: required for role %s" % (i, j, fn["role"]))
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
        for field, kinds in KIND_FIELDS:
            claim = x[field]
            if x["kind"] not in kinds and (claim["status"] != "not_found" or claim["evidence"]):
                errors.append("%s.%s: must be not_found without evidence unless kind is %s"
                              % (path, field, " or ".join(kinds)))
        _amount_errors(doc, x, path, errors)
        _supply_errors(x, path, errors)
    _alternative_errors(interfaces, errors)
    for i, t in enumerate(strategies):
        claim = t["deployment"]
        if t["component"] not in DEPLOYMENT_COMPONENTS and (claim["status"] != "not_found" or claim["evidence"]):
            errors.append("strategies[%d].deployment: must be not_found without evidence unless component is %s"
                          % (i, " or ".join(DEPLOYMENT_COMPONENTS)))
        if claim["value"] == "DEPLOYED_VERIFIED" and claim["status"] != "verified":
            errors.append("strategies[%d].deployment: DEPLOYED_VERIFIED requires status verified" % i)
    for i, z in enumerate(doc["supports"]):
        path = "supports[%d]" % i
        for j, t in enumerate(z["strategies"]):
            _need(t, tids, "%s.strategies[%d]" % (path, j), errors, "strategy")
        _need(z["provider"], eids, path + ".provider", errors, "entity")
        _need(z["beneficiary"], eids | pids, path + ".beneficiary", errors, "entity/product")
    for i, h in enumerate(doc["holder_rights"]):
        _need(h["product"], pids, "holder_rights[%d].product" % i, errors, "product")
    for i, e in enumerate(doc["flows"]["edges"]):
        for j, t in enumerate(e["strategies"]):
            _need(t, tids, "flows.edges[%d].strategies[%d]" % (i, j), errors, "strategy")
        _need(e["interface"], xids, "flows.edges[%d].interface" % i, errors, "interface")
    known = {"E": eids, "P": pids, "T": tids, "X": xids, "Z": ids["Z"]}
    _finding_errors(doc, known, errors)

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
        if t["component"] in SETTLED_COMPONENTS and t["id"] not in settled:
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
    _check_ids(doc["supports"], "Z", "supports", errors)
    _check_ids(nodes, "n", "flows.nodes", errors)
    _check_ids(searches, "N", "next_searches", errors)
    _check_ids(doc["issuer_requests"], "Q", "issuer_requests", errors)
    for prefix in ("G", "D", "C", "U", "R"):
        _check_ids([f for f in findings if f["id"][0] == prefix], prefix, "findings", errors)

    sids = {s["id"] for s in sources}
    eids = {e["id"] for e in entities}
    pids = {p["id"] for p in products}
    nids = {n["id"] for n in nodes}
    fids = {f["id"] for f in findings}
    ids = {"S": sids, "E": eids, "P": pids, "T": {t["id"] for t in doc["strategies"]},
           "X": {x["id"] for x in doc["interfaces"]}, "Z": {z["id"] for z in doc["supports"]}}

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
