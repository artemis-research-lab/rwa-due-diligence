"""Escaping, truncation and JSON helpers shared by the renderers and the run directory."""

import html
import json

# Characters escaped with a backslash in Markdown output. The backslash is handled first.
MD_SPECIAL = "\\|*_[]<>#`"


def has_control(text):
    """True if text contains a C0 control character or DEL."""
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in text)


def clip(text, limit):
    """Hard cut at limit characters (no ellipsis)."""
    if limit is None or len(text) <= limit:
        return text
    return text[:limit]


def md_escape(text):
    """Escape Markdown specials; newlines and other control characters become spaces."""
    text = text.replace("\r\n", " ")
    out = []
    for ch in text:
        if ord(ch) < 32 or ord(ch) == 127:
            out.append(" ")
        elif ch in MD_SPECIAL:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def md_text(text, limit=None):
    """Clip, then escape: the only way free text enters a Markdown render."""
    return md_escape(clip(text, limit))


def html_text(text, limit=None):
    """Clip, blank control characters, HTML-escape and ASCII-encode: the only way free text enters HTML."""
    text = clip(text, limit).replace("\r\n", " ")
    text = "".join(" " if ord(ch) < 32 or ord(ch) == 127 else ch for ch in text)
    return html.escape(text, quote=True).encode("ascii", "xmlcharrefreplace").decode("ascii")


def html_url(url):
    """Escaped URL for an href if it is plain http(s) without control characters or whitespace, else None."""
    if not url.lower().startswith(("https://", "http://")):
        return None
    if has_control(url) or any(ch.isspace() for ch in url):
        return None
    return html_text(url)


def _reject_constant(name):
    raise ValueError("non-finite number %s is not allowed" % name)


def load_json_text(text):
    """Parse JSON, rejecting NaN and Infinity."""
    return json.loads(text, parse_constant=_reject_constant)


def dump_json(value):
    """Canonical file form: 2-space indent, ASCII-safe, one trailing newline."""
    return json.dumps(value, indent=2, ensure_ascii=True) + "\n"


def dump_json_line(value):
    """Compact single-line form used for the JSONL ledger."""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n"


# --------------------------------------------------------------------------- shared render lines

def id_key(item):
    """Sort key for ids such as S12 or n3: prefix, then number."""
    ident = item["id"] if isinstance(item, dict) else item
    return (ident[0], int(ident[1:]))


def finding_line(finding, subjects=False, marker="", scope=False):
    """`- **G3** [topic] statement (S4, S9)`; the parenthesis is omitted without evidence.

    subjects=True appends ` -- subjects: X3.security, ...` when the finding names subjects; scope=True appends
    ` -- scope: <scope note>` when the note is not empty; marker (for example `[BLOCKING] `) is placed before the
    statement."""
    line = "- **%s** [%s] %s%s" % (finding["id"], finding["topic"], marker, md_text(finding["statement"], 280))
    if finding["evidence"]:
        line += " (%s)" % ", ".join(finding["evidence"])
    if subjects and finding.get("subjects"):
        line += " -- subjects: " + ", ".join(md_text(s) for s in finding["subjects"])
    if scope and finding.get("scope_note"):
        line += " -- scope: " + md_text(finding["scope_note"], 200)
    return line


def number_text(value):
    """A JSON number as text (`25000000`, `0.5`)."""
    return json.dumps(value)


def totals_text(bucket):
    """`<sum> <currency>` per currency, sorted by currency and joined by `; `; `--` when empty."""
    if not bucket:
        return "--"
    return "; ".join("%s %s" % (number_text(bucket[key]), md_text(key)) for key in sorted(bucket))


def request_line(request):
    """`- **Q1** (priority 1) request -- why (answers A2, C6)`."""
    return "- **%s** (priority %d) %s -- %s (answers %s)" % (
        request["id"], request["priority"], md_text(request["request"], 200), md_text(request["why"], 200),
        ", ".join(request["answers"]))


def search_line(search, suffix=""):
    """`- **N2** what -- where -- why (resolves G1, D2; est N calls)` followed by the fixed suffix text."""
    resolves = ", ".join(search["resolves"]) or "none"
    return "- **%s** %s -- %s -- %s (resolves %s; est %d calls)%s" % (
        search["id"], md_text(search["what"], 120), md_text(search["where"], 120),
        md_text(search["why"], 120), resolves, search["est_calls"], md_text(suffix))


# Appendix D suffixes (final reports): searches the analyst rejected, and the rest.
REJECTED_SUFFIX = " -- rejected by the analyst"
NOT_RUN_SUFFIX = " -- not run"


def not_run_suffix(search, rejected):
    return REJECTED_SUFFIX if search["id"] in rejected else NOT_RUN_SUFFIX
