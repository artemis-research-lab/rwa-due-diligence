"""Change log (v0.7.0 section 7.2): what changed between the record a run was seeded from (or an earlier final
version of the same run, v0.7.5) and the current record.

The earlier record is first migrated to the current schema (the caller passes migrate_to_current output), so a
change that is exactly the migration itself never shows. Claims are matched by claim id, objects by their ids
and findings by carried_from or by id (diff match); sources give an added row, or one changed row per corrected
attribution field (source_type, origin, publisher; v0.7.4). Pure and deterministic.
"""

import json
import re

from lib import framework, schema

TEXT_MAX = 80
# Objects compared leaf by leaf, by id: (section path, id prefix).
OBJECTS = ((("entities",), "E"), (("project", "products"), "P"), (("strategies",), "T"), (("interfaces",), "X"),
           (("supports",), "Z"), (("issuer_requests",), "Q"))
# How findings are paired (v0.7.5): carried_from for a seeded run, id between versions of one run.
MATCHES = ("carried_from", "id")


def _clip(text):
    return text if len(text) <= TEXT_MAX else text[:TEXT_MAX]


def _json(value):
    """A leaf as text: strings as they are, other values as JSON; clipped to TEXT_MAX."""
    return _clip(value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, sort_keys=True))


def _claim_text(claim):
    value = "null" if claim["value"] is None else framework.plain_value(claim["value"])
    return "%s [%s]" % (_clip(value), claim["status"])


def _is_claim(value):
    return isinstance(value, dict) and set(value) == set(schema.CLAIM_KEYS)


def _leaves(value, path=""):
    """[(path, leaf)] of non-claim leaves below value; claims are compared by claim id instead."""
    if _is_claim(value):
        return []
    if isinstance(value, dict):
        out = []
        for key, item in value.items():
            out += _leaves(item, "%s.%s" % (path, key) if path else key)
        return out
    if isinstance(value, list) and any(isinstance(item, dict) for item in value):
        out = []
        for i, item in enumerate(value):
            out += _leaves(item, "%s[%d]" % (path, i))
        return out
    return [(path, value)]


def _row(ref, path, change, before=None, after=None, evidence_added=()):
    return {"ref": ref, "path": path, "change": change, "before": before, "after": after,
            "evidence_added": list(evidence_added)}


def _section(doc, keys):
    value = doc
    for key in keys:
        value = value[key]
    return value


def _compare_leaves(ref, old, new, rows, skip=()):
    before = dict(_leaves(old))
    after = dict(_leaves(new))
    for path in sorted(set(before) | set(after)):
        if path in skip or path.split(".", 1)[0].split("[", 1)[0] in skip:
            continue
        if before.get(path, after.get(path)) == [] and any(p.startswith(path + "[") for p in set(before) | set(after)):
            continue  # an empty list whose entries appear on the other side
        if path not in before:
            rows.append(_row(ref, path, "added", None, _json(after[path])))
        elif path not in after:
            rows.append(_row(ref, path, "removed", _json(before[path]), None))
        elif before[path] != after[path]:
            rows.append(_row(ref, path, "changed", _json(before[path]), _json(after[path])))


def _claims(doc):
    return {framework.claim_id(parts, doc): claim for parts, claim in schema.iter_claims(doc)}


def _split(cid):
    match = re.match(r"^([A-Z][0-9]+)\.?(.*)$", cid)
    if match:
        return match.group(1), match.group(2)
    head = re.match(r"^([a-z_]+(\[[0-9]+\])?)\.?(.*)$", cid)
    return head.group(1), head.group(3)


def _pair_findings(old_doc, new_doc, match):
    """[(ref, old finding or None, new finding or None)]: by carried_from (a seeded run, whose ids were
    re-assigned) or by id (two versions of one run, whose ids are stable; v0.7.5)."""
    old_findings = {f["id"]: f for f in old_doc["findings"]}
    pairs = []
    matched = set()
    for f in new_doc["findings"]:
        key = f["id"] if match == "id" else f["carried_from"]
        source = old_findings.get(key) if key is not None else None
        if source is None:
            pairs.append((f["id"], None, f))
            continue
        matched.add(source["id"])
        pairs.append((f["id"] if source["id"] == f["id"] else "%s -> %s" % (source["id"], f["id"]), source, f))
    pairs += [(ident, f, None) for ident, f in old_findings.items() if ident not in matched]
    return pairs


def diff(old_doc, new_doc, match="carried_from"):
    """Change rows {ref, path, change, before, after, evidence_added} sorted by ref then path; [] when old_doc
    is None. match pairs findings by "carried_from" (the seeded change log) or by "id" (amendment change logs,
    where carried_from is compared like any other leaf)."""
    if match not in MATCHES:
        raise ValueError("match must be one of %s, not %r" % (", ".join(MATCHES), match))
    if old_doc is None:
        return []
    rows = []
    whole = set()
    for keys, prefix in OBJECTS:
        old = {item["id"]: item for item in _section(old_doc, keys)}
        new = {item["id"]: item for item in _section(new_doc, keys)}
        for ident in sorted(set(old) | set(new)):
            if ident not in old:
                rows.append(_row(ident, "", "added"))
                whole.add(ident)
            elif ident not in new:
                rows.append(_row(ident, "", "removed"))
                whole.add(ident)
            else:
                _compare_leaves(ident, old[ident], new[ident], rows, skip=("id",))

    skip = ("id",) if match == "id" else ("id", "carried_from")
    for ref, old, new in _pair_findings(old_doc, new_doc, match):
        if old is None:
            rows.append(_row(ref, "", "added", None, _json(new["statement"])))
        elif new is None:
            rows.append(_row(ref, "", "removed", _json(old["statement"]), None))
        else:
            _compare_leaves(ref, old, new, rows, skip=skip)

    old_sources = {s["id"]: s for s in old_doc["sources"]}
    for s in new_doc["sources"]:
        old = old_sources.get(s["id"])
        if old is None:
            rows.append(_row(s["id"], "", "added", None, _json(s["title"])))
            continue
        for key in schema.CORRECTABLE:  # ledger corrections (v0.7.4 section 4)
            if old.get(key) != s[key]:
                rows.append(_row(s["id"], key, "changed", _json(old.get(key)), _json(s[key])))

    old_claims = _claims(old_doc)
    new_claims = _claims(new_doc)
    for cid in sorted(set(old_claims) | set(new_claims)):
        ref, path = _split(cid)
        if ref in whole:
            continue
        before, after = old_claims.get(cid), new_claims.get(cid)
        if before is None:
            rows.append(_row(ref, path, "added", None, _claim_text(after), after["evidence"]))
        elif after is None:
            rows.append(_row(ref, path, "removed", _claim_text(before), None))
        elif before != after:
            added = [sid for sid in after["evidence"] if sid not in before["evidence"]]
            text = _claim_text(after)
            only_added = set(before["evidence"]) <= set(after["evidence"])  # shown in evidence_added
            keys = [k for k in schema.CLAIM_KEYS if k not in ("value", "status") and before[k] != after[k]
                    and not (k == "evidence" and only_added)]
            if keys:
                text += " (%s changed)" % ", ".join(keys)
            rows.append(_row(ref, path, "changed", _claim_text(before), text, added))
    return sorted(rows, key=lambda r: (_natural(r["ref"]), _natural(r["path"])))


def _natural(text):
    return [(0, int(part), "") if part.isdigit() else (1, 0, part) for part in re.split(r"([0-9]+)", text)]
