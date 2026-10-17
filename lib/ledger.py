"""Source ledger: append-only JSONL, script clock, excerpt sha256 (D13)."""

import datetime
import hashlib

from lib import schema, validate
from lib.textutil import dump_json_line, load_json_text

TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def system_clock():
    """The real clock; lib code takes a clock parameter so tests can inject a fixed one."""
    return datetime.datetime.now(datetime.timezone.utc)


def format_ts(moment):
    if moment.tzinfo is not None:
        moment = moment.astimezone(datetime.timezone.utc)
    return moment.strftime(TS_FORMAT)


def excerpt_sha256(excerpt):
    return hashlib.sha256(excerpt.encode("utf-8")).hexdigest()


def read_ledger(path):
    if not path.exists():
        return []
    entries = []
    for line in path.read_bytes().decode("utf-8").split("\n"):
        if line.strip():
            entries.append(load_json_text(line))
    return entries


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


def append_line(path, source):
    """Append one line; existing bytes are never rewritten."""
    with path.open("ab") as handle:
        handle.write(dump_json_line(source).encode("utf-8"))
