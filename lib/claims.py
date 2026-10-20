"""Claim rules (section 3.3, v0.6.0 third_party_reported, v0.7.0 provenance) and per-claim independence
derivation (D3, D14).

Legal paths are the sections in schema.LEGAL_SECTIONS; coded-claim value checks (D39) live in validate.py.
Provenance (curator Q8): origin is who asserted the fact, the evidence sources are where it was published and
assurance is what an auditor or reviewer tested for this precise claim. The Q8 auditor-source rules apply only once
origin is set: a null origin means unstated (lint warning, QA7 failure, finalize refuses). Claims under audits[]
describe the audit itself and are exempt from them (CChat decision during the v0.7.0 build).
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


# Origins that may verify a claim citing an auditor source (curator Q8).
AUDITED_VERIFIED_ORIGINS = ("auditor_procedure", "regulator", "registry", "onchain")
# Sections whose claims describe an audit itself (exempt from the Q8 auditor-source rules).
AUDIT_SECTIONS = ("audits",)


def q8_exempt(parts):
    return bool(parts) and parts[0] in AUDIT_SECTIONS


def check_claim(parts, claim, sources_by_id, subject_ids):
    """Return error strings for one claim."""
    path = schema.format_path(parts)
    errors = []
    evidence = claim["evidence"]
    status = claim["status"]
    note = claim["note"]
    subject = claim["subject"]
    origin = claim["origin"]
    assurance = claim["assurance"]

    if subject is not None and subject not in subject_ids:
        errors.append("%s.subject: unknown id %s" % (path, subject))

    roles = []
    source_origins = []
    for sid in evidence:
        source = sources_by_id.get(sid)
        if source is None:
            errors.append("%s.evidence: unknown source %s" % (path, sid))
        else:
            roles.append(evidence_role(source, claim))
            source_origins.append(source.get("origin"))
    independent = [r.split(":", 1)[1] for r in roles if r.startswith("independent:")]
    cites_auditor = "auditor" in source_origins
    q8 = cites_auditor and origin is not None and not q8_exempt(parts)  # Q8 auditor-source rules apply
    issuer_origin = origin in schema.ISSUER_ORIGINS

    if status != "not_found" and claim["value"] is None:
        errors.append("%s: %s requires a non-null value" % (path, status))

    if status == "verified":
        audited_ok = not q8 or (assurance == "TESTED" and origin in AUDITED_VERIFIED_ORIGINS)
        if not audited_ok:
            errors.append("%s: verified with an auditor source requires assurance TESTED for this claim "
                          "(curator Q8)" % path)
        if is_legal_path(parts):
            verifiers = [o for o in independent if o in LEGAL_VERIFIERS and (o != "auditor" or audited_ok)]
            if not verifiers:
                errors.append("%s: verified requires a regulator/registry/auditor/onchain source for legal fields"
                              % path)
        elif not independent:
            errors.append("%s: verified requires an independent source" % path)
        if "analyst" in roles:
            errors.append("%s: verified must not cite an analyst source" % path)
    elif status == "self_reported":
        if "self" not in roles and not (issuer_origin and evidence):
            errors.append("%s: self_reported requires a first-party or subject-published source" % path)
    elif status == "third_party_reported":
        if not independent:
            errors.append("%s: third_party_reported requires an independent source" % path)
        elif (q8 and all(o == "auditor" for o in independent)
              and origin not in ("independent_party", "auditor_procedure")):
            errors.append("%s: auditor source: state origin (issuer statement -> self_reported; tested -> "
                          "auditor_procedure)" % path)
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
        if origin is not None or assurance is not None:
            errors.append("%s: not_found requires null origin and assurance" % path)

    if issuer_origin and status not in ("self_reported", "not_found"):
        errors.append("%s: origin %s is an issuer assertion; status must be self_reported (curator Q8)"
                      % (path, origin))
    if origin == "auditor_procedure":
        if not cites_auditor:
            errors.append("%s: origin auditor_procedure requires an auditor source" % path)
        if assurance not in ("TESTED", "NOT_TESTED"):
            errors.append("%s: origin auditor_procedure requires assurance TESTED or NOT_TESTED" % path)
    if origin == "analyst" and status in ("verified", "self_reported", "third_party_reported"):
        errors.append("%s: origin analyst allows only inferred or not_found" % path)
    if assurance is not None and not independent:
        errors.append("%s: assurance requires an auditor or independent source" % path)
    return errors


def check_all(doc):
    sources_by_id = {s["id"]: s for s in doc["sources"]}
    subject_ids = {e["id"] for e in doc["entities"]} | {p["id"] for p in doc["project"]["products"]}
    errors = []
    for parts, claim in schema.iter_claims(doc):
        errors.extend(check_claim(parts, claim, sources_by_id, subject_ids))
    return errors
