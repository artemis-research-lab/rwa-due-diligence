"""Source ledger: append-only JSONL, script clock, excerpt sha256 (D13); correction lines fix a source's
attribution without editing earlier bytes (D88)."""

import datetime
import hashlib

from lib import schema, validate
from lib.textutil import dump_json_line, load_json_text

TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CORRECTION_KEYS = ("correction", "fields", "previous", "reason", "corrected_at")


class ContractError(Exception):
    """Path, state or ledger contract violation (CLI exit 3); lib/runstate.py re-exports it."""


def system_clock():
    """The real clock; lib code takes a clock parameter so tests can inject a fixed one."""
    return datetime.datetime.now(datetime.timezone.utc)


def format_ts(moment):
    if moment.tzinfo is not None:
        moment = moment.astimezone(datetime.timezone.utc)
    return moment.strftime(TS_FORMAT)


def excerpt_sha256(excerpt):
    return hashlib.sha256(excerpt.encode("utf-8")).hexdigest()


def _lines(path):
    """[(line number, parsed JSON)] of the non-empty ledger lines; ContractError naming a malformed line."""
    if not path.exists():
        return []
    out = []
    for number, line in enumerate(path.read_bytes().decode("utf-8").split("\n"), start=1):
        if line.strip():
            try:
                out.append((number, load_json_text(line)))
            except ValueError as exc:
                raise ContractError("%s line %d: not valid JSON: %s" % (path.name, number, exc))
    return out


def _is_correction(entry):
    return isinstance(entry, dict) and "correction" in entry


def correction_errors(correction, sources_by_id):
    """Errors of one correction line against the sources as corrected so far (empty means valid)."""
    if not isinstance(correction, dict) or sorted(correction) != sorted(CORRECTION_KEYS):
        return ["keys must be %s" % ", ".join(CORRECTION_KEYS)]
    sid, fields, previous, reason = (correction["correction"], correction["fields"], correction["previous"],
                                     correction["reason"])
    if sid not in sources_by_id:
        return ["correction of unknown source %r" % (sid,)]
    source = sources_by_id[sid]
    if not isinstance(fields, dict) or not fields or any(k not in schema.CORRECTABLE for k in fields):
        return ["fields: one or more of %s" % ", ".join(schema.CORRECTABLE)]
    if not isinstance(previous, dict) or sorted(previous) != sorted(fields):
        return ["previous: must name the same fields"]
    errors = []
    for key, value in sorted(fields.items()):
        if previous[key] != source[key]:
            errors.append("previous.%s: %r is not the current value %r" % (key, previous[key], source[key]))
        if value == source[key]:
            errors.append("fields.%s: %r equals the current value" % (key, value))
    if not isinstance(reason, str) or not (
            schema.CORRECTION_REASON_MIN <= len(reason) <= schema.CORRECTION_REASON_MAX):
        errors.append("reason: must be %d..%d characters" % (schema.CORRECTION_REASON_MIN,
                                                             schema.CORRECTION_REASON_MAX))
    try:
        datetime.datetime.strptime(correction["corrected_at"], TS_FORMAT)
    except (TypeError, ValueError):
        errors.append("corrected_at: must be a timestamp YYYY-MM-DDTHH:MM:SSZ")
    errors += [e.replace("(root)", "source") for e in validate.structural_errors(dict(source, **fields),
                                                                                  schema.SOURCE)]
    return errors


def _fold(path):
    """(sources with the corrections applied in file order, correction lines)."""
    sources, corrections = [], []
    by_id = {}
    for number, entry in _lines(path):
        if not _is_correction(entry):
            sources.append(entry)
            if isinstance(entry, dict):
                by_id[entry.get("id")] = entry
            continue
        errors = correction_errors(entry, by_id)
        if errors:
            raise ContractError("%s line %d: %s" % (path.name, number, "; ".join(errors)))
        by_id[entry["correction"]].update(entry["fields"])
        corrections.append(entry)
    return sources, corrections


def read_ledger(path):
    """Source list with every correction line applied in file order (the document's sources must equal it)."""
    return _fold(path)[0]


def read_corrections(path):
    """The correction lines of the ledger, in file order."""
    return _fold(path)[1]


def make_correction(source, fields, reason, clock):
    """The correction line for source with the new field values; raises ValueError with the errors."""
    correction = {"correction": source["id"], "fields": dict(fields),
                  "previous": {key: source[key] for key in fields}, "reason": reason,
                  "corrected_at": format_ts(clock())}
    errors = correction_errors(correction, {source["id"]: source})
    if errors:
        raise ValueError(errors)
    return correction


def make_source(index, url, title, source_type, origin, fetch, excerpt, clock,
                publisher=None, archived=False, version_date=None, note="", offline=False):
    """Build the source object for id S<index>; raises ValueError with the schema errors."""
    source = {
        "id": "S%d" % index,
        "url": url,
        "title": title,
        "source_type": source_type,
        "origin": origin,
        "publisher": publisher,
        "retrieved_at": None if offline else format_ts(clock()),
        "fetch": "offline" if offline else fetch,
        "excerpt": excerpt,
        "excerpt_sha256": excerpt_sha256(excerpt),
        "archived": bool(archived),
        "version_date": version_date,
        "note": note,
    }
    errors = validate.structural_errors(source, schema.SOURCE)
    if errors:
        raise ValueError(sorted(set(e.replace("(root)", "source") for e in errors)))
    return source


def append_line(path, entry):
    """Append one line (a source or a correction); existing bytes are never rewritten."""
    with path.open("ab") as handle:
        handle.write(dump_json_line(entry).encode("utf-8"))
