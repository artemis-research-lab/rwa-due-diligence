"""Escaping, truncation and JSON helpers shared by the renderers and the run directory."""

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


def finding_line(finding):
    """`- **G3** [topic] statement (S4, S9)`; the parenthesis is omitted without evidence."""
    line = "- **%s** [%s] %s" % (finding["id"], finding["topic"], md_text(finding["statement"], 280))
    if finding["evidence"]:
        line += " (%s)" % ", ".join(finding["evidence"])
    return line


def search_line(search):
    """`- **N2** what -- where -- why (resolves G1, D2; est N calls)`."""
    resolves = ", ".join(search["resolves"]) or "none"
    return "- **%s** %s -- %s -- %s (resolves %s; est %d calls)" % (
        search["id"], md_text(search["what"], 120), md_text(search["where"], 120),
        md_text(search["why"], 120), resolves, search["est_calls"])
