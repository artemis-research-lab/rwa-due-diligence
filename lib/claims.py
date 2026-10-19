"""Claim rules (section 3.3) and per-claim independence derivation (D3, D14).

Legal paths are the sections in schema.LEGAL_SECTIONS; coded-claim value checks (D39) live in validate.py.
"""

from lib import schema

LEGAL_VERIFIERS = ("regulator", "registry", "auditor", "onchain")


def is_legal_path(parts):
    return bool(parts) and parts[0] in schema.LEGAL_SECTIONS


def evidence_role(source, claim):
    """Role of a source for a claim: 'self', 'analyst' or 'independent:<origin>'."""
    origin = source.get("origin")
    publisher = source.get("publisher")
    if origin == "first_party" or (publisher is not None and publisher == claim.get("subject")):
        return "self"
    if origin == "analyst":
        return "analyst"
    return "independent:%s" % origin


def check_claim(parts, claim, sources_by_id, subject_ids):
    """Return error strings for one claim."""
    path = schema.format_path(parts)
    errors = []
    evidence = claim["evidence"]
    status = claim["status"]
    note = claim["note"]
    subject = claim["subject"]

    if subject is not None and subject not in subject_ids:
        errors.append("%s.subject: unknown id %s" % (path, subject))

    roles = []
    for sid in evidence:
        source = sources_by_id.get(sid)
        if source is None:
            errors.append("%s.evidence: unknown source %s" % (path, sid))
        else:
            roles.append(evidence_role(source, claim))
    independent = [r.split(":", 1)[1] for r in roles if r.startswith("independent:")]

    if status != "not_found" and claim["value"] is None:
        errors.append("%s: %s requires a non-null value" % (path, status))

    if status == "verified":
        if is_legal_path(parts):
            if not any(o in LEGAL_VERIFIERS for o in independent):
                errors.append("%s: verified requires a regulator/registry/auditor/onchain source for legal fields"
                              % path)
        elif not independent:
            errors.append("%s: verified requires an independent source" % path)
        if "analyst" in roles:
            errors.append("%s: verified must not cite an analyst source" % path)
    elif status == "self_reported":
        if "self" not in roles:
            errors.append("%s: self_reported requires a first-party or subject-published source" % path)
    elif status == "inferred":
        if not evidence:
            errors.append("%s: inferred requires at least one evidence" % path)
        if not note:
            errors.append("%s: inferred requires a note" % path)
    elif status == "not_found":
        if claim["value"] is not None:
            errors.append("%s: not_found requires a null value" % path)
        if evidence and not note:
            errors.append("%s: not_found with evidence requires a note" % path)
    return errors


def check_all(doc):
    sources_by_id = {s["id"]: s for s in doc["sources"]}
    subject_ids = {e["id"] for e in doc["entities"]} | {p["id"] for p in doc["project"]["products"]}
    errors = []
    for parts, claim in schema.iter_claims(doc):
        errors.extend(check_claim(parts, claim, sources_by_id, subject_ids))
    return errors
