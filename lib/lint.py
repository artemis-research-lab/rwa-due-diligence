"""Lint (dd.py lint): warnings the analyst must fix before review; never errors.

Address warnings flag EVM addresses whose letters are all lowercase or all uppercase. The check is case shape
only: EIP-55 needs keccak-256, which the standard library lacks, so a mixed-case address with a wrong checksum is
not detected. Strings inside the sources array are not checked.
Layer, claim and path warnings (v0.6.0 2.3) and amount and provenance warnings (v0.7.0 2.3) need a structurally
valid document.
"""

import re

from lib import claims, framework, schema

ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")


def _strings(node, parts):
    if isinstance(node, str):
        yield parts, node
    elif isinstance(node, dict):
        for key, value in node.items():
            if not parts and key == "sources":
                continue
            yield from _strings(value, parts + (key,))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, parts + (i,))


def _single_case(address):
    letters = [ch for ch in address[2:] if ch.isalpha()]
    return bool(letters) and (all(ch.islower() for ch in letters) or all(ch.isupper() for ch in letters))


def address_warnings(doc):
    """[{"path", "address"}, ...] sorted by path then address, without duplicates."""
    found = set()
    for parts, text in _strings(doc, ()):
        for match in ADDRESS.finditer(text):
            if _single_case(match.group(0)):
                found.add((schema.format_path(parts), match.group(0)))
    return [{"path": path, "address": address} for path, address in sorted(found)]


# --------------------------------------------------------------------------- v0.6.0 layer, claim and path

# kind -> (expected layer of `from`, expected layer of `to`); None means not checked.
LAYERED = {
    "holder_L1": (None, "L1"),
    "L1_L2": ("L1", "L2"),
    "L2_L3": ("L2", "L3"),
    "L3_L3O": ("L3", "L3-O"),
    "within_L1": ("L1", "L1"),
    "within_L2": ("L2", "L2"),
    "within_L3": ("L3", "L3"),
    "sleeve_holding": ("L1", None),
}
POOL_CLAIMS = ("DL", "DI", "AP", "PI")
CREDIT_COMPONENTS = ("CORE_CREDIT", "DEFI_LENDING")


def _warning(path, message):
    return {"path": path, "message": message}


def _has_layer(entity, layer, strategy_id):
    return entity is not None and any(fn["layer"] == layer and fn["strategy"] in (strategy_id, None)
                                      for fn in entity["functions"])


def layer_warnings(doc):
    entities = {e["id"]: e for e in doc["entities"]}
    out = []
    for i, x in enumerate(doc["interfaces"]):
        expected = LAYERED.get(x["kind"])
        if expected is None:
            continue
        for end, layer in zip(("from", "to"), expected):
            if layer is None or _has_layer(entities.get(x[end]), layer, x["strategy"]):
                continue
            out.append(_warning("interfaces[%d]" % i, "%s: %s but %s has no %s function for %s"
                                % (x["id"], x["kind"], x[end], layer, x["strategy"])))
    return out


def claim_warnings(doc):
    sources = {s["id"]: s for s in doc["sources"]}
    out = []
    for i, t in enumerate(doc["strategies"]):
        claim = t["deployment"]
        if t["component"] in CREDIT_COMPONENTS and claim["status"] == "not_found" and not claim["evidence"]:
            out.append(_warning("strategies[%d].deployment" % i,
                                "%s.deployment: not set for a credit strategy" % t["id"]))
    for i, x in enumerate(doc["interfaces"]):
        claim = x["legal_class"]
        if x["kind"] != "L1_L2" or x["route"]["value"] != "POOL" or claim["value"] not in POOL_CLAIMS:
            continue
        if any(sources.get(sid, {}).get("source_type") == "legal_doc" for sid in claim["evidence"]):
            continue
        out.append(_warning("interfaces[%d].legal_class" % i,
                            "%s: POOL with legal class %s needs a contract (legal_doc) source; use "
                            "PROTOCOL_ENTITLEMENT or leave it not_found" % (x["id"], claim["value"])))
    return out


def path_warnings(doc):
    entities = {e["id"]: e for e in doc["entities"]}
    out = []
    for i, t in enumerate(doc["strategies"]):
        sid = t["id"]
        kinds = [x["kind"] for x in doc["interfaces"] if x["strategy"] == sid]
        missing = []
        if t["component"] in CREDIT_COMPONENTS:
            l1_to_l3 = any(x["strategy"] == sid and x["kind"] == "L2_L3"
                           and _has_layer(entities.get(x["from"]), "L1", sid) for x in doc["interfaces"])
            if "holder_L1" not in kinds:
                missing.append("holder_L1")
            if "L1_L2" not in kinds and not l1_to_l3:
                missing.append("L1_L2")
            if "L2_L3" not in kinds:
                missing.append("L2_L3")
        elif "sleeve_holding" not in kinds:
            missing.append("sleeve_holding")
        out += [_warning("strategies[%d]" % i, "%s: no %s interface" % (sid, kind)) for kind in missing]
    for i, f in enumerate(doc["findings"]):
        if f["blocking"] and not f["material"] and not f["k_checks"] and not f["impact"]:
            out.append(_warning("findings[%d]" % i, "%s: blocking finding without k_checks or impact (section 1 "
                                                    "cannot place it)" % f["id"]))
    return out


# --------------------------------------------------------------------------- v0.7.0 amount and provenance

YEAR = re.compile(r"(?<![0-9])[0-9]{4}(?![0-9])")


def amount_warnings(doc):
    origins = {s["id"]: s["origin"] for s in doc["sources"]}
    out = []
    for i, x in enumerate(doc["interfaces"]):
        for j, a in enumerate(x["amounts"]):
            path = "interfaces[%d].amounts[%d]" % (i, j)
            ref = "%s.amounts[%d]" % (x["id"], j)
            onchain = any(origins.get(sid) == "onchain" for sid in a["value"]["evidence"])
            if onchain and (a["block"] is None or a["chain"] is None):
                out.append(_warning(path, "%s: on-chain amount without block and chain" % ref))
            if a["as_of"] is None:
                out.append(_warning(path, "%s: no observation time; it will not be counted" % ref))
            if a["basis"] == "CUMULATIVE_FUNDED" and not YEAR.search(a["scope"]):
                out.append(_warning(path, "%s: CUMULATIVE_FUNDED scope should state the period" % ref))
        if x["kind"] in ("L1_L2", "sleeve_holding") and x["amounts"] and not any(
                a["basis"] in schema.COUNTABLE for a in x["amounts"]):
            out.append(_warning("interfaces[%d]" % i, "%s: no countable basis (%s)"
                                % (x["id"], ", ".join(schema.COUNTABLE))))
    return out


def provenance_warnings(doc):
    origins = {s["id"]: s["origin"] for s in doc["sources"]}
    out = []
    for parts, claim in schema.iter_claims(doc):
        if claim["status"] == "not_found" or claim["origin"] is not None or claims.q8_exempt(parts):
            continue
        if any(origins.get(sid) == "auditor" for sid in claim["evidence"]):
            out.append(_warning(schema.format_path(parts), "%s: cites an auditor source; set origin and assurance "
                                                            "(curator Q8)" % framework.claim_id(parts, doc)))
    return out


def _sorted(warnings):
    return sorted(warnings, key=lambda w: (w["path"], w["message"]))


def lint(doc):
    """All warnings of a structurally valid document, each list sorted by path then message."""
    return {"address_warnings": address_warnings(doc), "layer_warnings": _sorted(layer_warnings(doc)),
            "claim_warnings": _sorted(claim_warnings(doc)), "path_warnings": _sorted(path_warnings(doc)),
            "amount_warnings": _sorted(amount_warnings(doc)),
            "provenance_warnings": _sorted(provenance_warnings(doc))}
