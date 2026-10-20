"""Quantitative and provenance checks (v0.7.0 section 6, v0.7.1 sections 1 and 4, dd.py qa): rules QA1-QA12 and
analyst expectations.

Each rule recomputes what it asserts from the document (independently of allocation_totals) and compares;
results are {"id", "rule", "result": "pass"|"fail", "detail"} with offending ids sorted, or `ok`.
"""

import json
import re

from lib import claims, framework, schema
from lib.textutil import load_json_text

STOCK_FLOW = ("CUMULATIVE_FUNDED", "FACILITY_COMMITMENT", "UNDRAWN_COMMITMENT")
CREDIT_COMPONENTS = ("CORE_CREDIT", "DEFI_LENDING")
EXPECT_KEYS = ("id", "case", "path", "op", "value")
COUNTED_PATH = re.compile(r"^(X[1-9][0-9]*)\.amounts\[([0-9]+)\]$")


class ExpectationError(ValueError):
    """Malformed expectation file or entry (CLI exit 3)."""


def _ref(row):
    return "%s.amounts[%d]" % (row[2], row[3])


def _natural(ident):
    """Sort key with numbers in natural order (X2 before X10)."""
    return [(0, int(part), "") if part.isdigit() else (1, 0, part) for part in re.split(r"([0-9]+)", ident)]


def _result(rule_id, name, offenders, info=()):
    offenders = sorted(set(offenders), key=_natural)
    if offenders:
        return {"id": rule_id, "rule": name, "result": "fail", "detail": ", ".join(offenders)}
    detail = "ok" if not info else "ok; unverified: " + ", ".join(sorted(set(info), key=_natural))
    return {"id": rule_id, "rule": name, "result": "pass", "detail": detail}


# --------------------------------------------------------------------------- rules

def _qa1(doc, rows):
    reported = framework.allocation_totals(doc)
    counted = [r for r in rows if r[10]]
    strategy_products = {t["id"]: t["products"] for t in doc["strategies"]}
    groups = {"strategies": {}, "components": {}, "products": {}}
    for row in counted:
        names = [("strategies", row[0]), ("components", row[1])]
        names += [("products", p) for p in strategy_products.get(row[0], [])]
        for scope, name in names:
            bucket = groups[scope].setdefault(name, {})
            key = framework.total_key(row)
            bucket[key] = bucket.get(key, 0) + row[5]
    offenders = []
    for scope in ("strategies", "components", "products"):
        names = set(groups[scope]) | set(reported.get(scope, {}))
        for name in names:
            got = {}
            for total in reported.get(scope, {}).get(name, []):
                key = (total["basis"], total["unit"], total["as_of"], total["valuation_basis"] or "")
                if key in got:
                    offenders.append(name)
                got[key] = got.get(key, 0) + total["sum"]
            if got != groups[scope].get(name, {}):
                offenders.append(name)
    return _result("QA1", "basis", offenders)


def run(doc, expectations=None):
    """Results of QA1-QA12 then one E:<id> result per expectation, in that order."""
    rows = framework.allocation(doc)
    counted = [r for r in rows if r[10]]
    interfaces = {x["id"]: x for x in doc["interfaces"]}
    origins = {s["id"]: s["origin"] for s in doc["sources"]}
    results = [_qa1(doc, rows)]

    results.append(_result("QA2", "lookthrough", [
        _ref(r) for r in counted if r[7] == "RESERVE_LOOKTHROUGH" or r[4] == "reserve_lookthrough"]))
    results.append(_result("QA3", "alternative", [
        _ref(r) for r in counted if interfaces[r[2]]["alternative"]["group"] is not None]))
    unverified = ["%s.amounts[%d]" % (x["id"], j) for x in doc["interfaces"] for j, a in enumerate(x["amounts"])
                  if a["basis"] == "SALE_PROCEEDS" and a["value"]["status"] != "verified"]
    results.append(_result("QA4", "proceeds", [_ref(r) for r in counted if r[7] == "SALE_PROCEEDS"], unverified))
    results.append(_result("QA5", "asof", [_ref(r) for r in counted if r[8] is None]))
    labelled = [name for scope in framework.allocation_totals(doc).values() for name, totals in scope.items()
                for t in totals if t["basis"] in STOCK_FLOW]
    results.append(_result("QA6", "stockflow", [_ref(r) for r in counted if r[7] in STOCK_FLOW] + labelled))

    provenance = []
    for parts, claim in schema.iter_claims(doc):
        source_origins = [origins.get(sid) for sid in claim["evidence"]]
        cites_auditor = "auditor" in source_origins and not claims.q8_exempt(parts)
        status = claim["status"]
        if ((cites_auditor and status != "not_found" and claim["origin"] is None)
                or (claim["origin"] in schema.ISSUER_ORIGINS and status not in ("self_reported", "not_found"))
                or claims.provenance_errors(parts, claim, source_origins)):
            provenance.append(framework.claim_id(parts, doc))
    results.append(_result("QA7", "provenance", provenance))

    flagged = [cid for cid, fl in framework.flags_by_id(doc).items() if fl == "CONFLICTING"]
    qualifying = [s for f in doc["findings"] if f["type"] == "discrepancy" and f["scope_match"] == "matched"
                  and f["resolution"]["status"] == "open" and len(f["assertions"]) >= 2 for s in f["subjects"]]
    other = [s for f in doc["findings"] if f["type"] in ("scope_unresolved", "unreconciled_transaction")
             for s in f["subjects"]]

    def covered(cid, subjects):
        return any(cid == s or cid.startswith(s + ".") or cid.startswith(s + "[") for s in subjects)
    results.append(_result("QA8", "conflicts", [cid for cid in flagged
                                                if not covered(cid, qualifying) or covered(cid, other)]))

    placeholders = [f["id"] for f in doc["findings"] if schema.is_placeholder(f["scope_note"])]
    placeholders += ["%s.amounts[%d]" % (x["id"], j) for x in doc["interfaces"] for j, a in enumerate(x["amounts"])
                     if a["scope"] == schema.MIGRATED_AMOUNT_SCOPE]
    results.append(_result("QA9", "placeholder", placeholders))

    shown = set(framework.critical(doc))
    results.append(_result("QA10", "section1", [
        f["id"] for f in doc["findings"]
        if (f["material"] or (f["blocking"] and f["k_checks"])) and f["id"] not in shown]))
    results.append(_result("QA11", "deployment", [
        t["id"] for t in doc["strategies"] if t["component"] in CREDIT_COMPONENTS
        and t["deployment"]["value"] == "DEPLOYED_VERIFIED" and t["deployment"]["status"] != "verified"]))
    per_interface = {}
    for r in counted:
        per_interface[r[2]] = per_interface.get(r[2], 0) + 1
    results.append(_result("QA12", "onemeasure", [xid for xid, n in per_interface.items() if n > 1]))

    for entry in expectations or []:
        results.append(check_expectation(doc, entry, rows))
    return results


def failed(results):
    """Ids of the failed results, in result order."""
    return [r["id"] for r in results if r["result"] == "fail"]


# --------------------------------------------------------------------------- expectations

def _entry_errors(i, entry):
    where = "expectations[%d]" % i
    if not isinstance(entry, dict):
        return "%s: must be an object" % where
    if sorted(entry) != sorted(EXPECT_KEYS):
        return "%s: keys must be %s" % (where, ", ".join(EXPECT_KEYS))
    ident, case, path, op = entry["id"], entry["case"], entry["path"], entry["op"]
    if not isinstance(ident, str) or not 1 <= len(ident) <= 20:
        return "%s.id: must be a string of 1..20 characters" % where
    if not isinstance(case, str) or len(case) > 120:
        return "%s.case: must be a string of at most 120 characters" % where
    if not isinstance(path, str) or not framework.RESOLVE_PATTERN.match(path):
        return "%s.path: not a resolvable path" % where
    if op not in schema.EXPECT_OPS:
        return "%s.op: must be one of %s" % (where, ", ".join(schema.EXPECT_OPS))
    value = entry["value"]
    if op == "in" and not isinstance(value, list):
        return "%s.value: must be a list for op in" % where
    if op in ("counted", "exists") and not isinstance(value, bool):
        return "%s.value: must be a boolean for op %s" % (where, op)
    if op in ("status", "flag", "not_contains") and not isinstance(value, str):
        return "%s.value: must be a string for op %s" % (where, op)
    return None


def parse_expectations(text, name="expectations"):
    """Validated list of expectation entries; ExpectationError naming the first malformed entry."""
    try:
        entries = load_json_text(text)
    except ValueError as exc:
        raise ExpectationError("%s: not valid JSON: %s" % (name, exc))
    if not isinstance(entries, list):
        raise ExpectationError("%s: must be a JSON array" % name)
    seen = set()
    for i, entry in enumerate(entries):
        error = _entry_errors(i, entry)
        if error is None and entry["id"] in seen:
            error = "expectations[%d].id: duplicate id %s" % (i, entry["id"])
        if error is not None:
            raise ExpectationError(error)
        seen.add(entry["id"])
    return entries


def _text(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _flag(doc, node):
    for parts, claim in schema.iter_claims(doc):
        if claim is node:
            return framework.flags(doc)[parts]
    return None


def _counted(doc, path, rows):
    match = COUNTED_PATH.match(path)
    if match is None:
        raise KeyError(path)
    framework.resolve(doc, path)
    entry = (match.group(1), int(match.group(2)))
    return any(row[10] for row in rows if (row[2], row[3]) == entry)


def check_expectation(doc, entry, rows=None):
    rows = framework.allocation(doc) if rows is None else rows
    op, path, expected = entry["op"], entry["path"], entry["value"]
    try:
        if op == "exists":
            try:
                framework.resolve(doc, path)
                actual = True
            except KeyError:
                actual = False
            ok = actual == expected
        elif op == "counted":
            actual = _counted(doc, path, rows)
            ok = actual == expected
        else:
            kind, node = framework.resolve(doc, path)
            value = node["value"] if kind == "claim" else node
            if op == "equals":
                actual, ok = value, value == expected
            elif op == "in":
                actual, ok = value, value in expected
            elif op == "status":
                if kind != "claim":
                    raise KeyError(path)
                actual = node["status"]
                ok = actual == expected
            elif op == "flag":
                if kind != "claim":
                    raise KeyError(path)
                actual = _flag(doc, node)
                ok = actual == expected
            else:  # not_contains
                text = value if isinstance(value, str) else ("" if value is None else framework.plain_value(value))
                actual, ok = value, expected.lower() not in text.lower()
        actual_text = _text(actual)
    except KeyError:
        ok, actual_text = False, "missing"
    return {"id": "E:" + entry["id"], "rule": entry["case"], "result": "pass" if ok else "fail",
            "detail": "%s %s %s -> %s" % (path, op, _text(expected), actual_text)}
