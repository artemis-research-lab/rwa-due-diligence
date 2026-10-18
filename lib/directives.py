"""Analyst directive grammar (section 3.6)."""

import re

_N = r"N[1-9][0-9]*"
_GD = r"[GD][1-9][0-9]*"
_WS = r"[ \t]+"

_RULES = (
    ("accept", re.compile(r"^accept%s(%s)$" % (_WS, _N)), ("id",)),
    ("reject", re.compile(r"^reject%s(%s)$" % (_WS, _N)), ("id",)),
    ("add-source", re.compile(r"^add-source%s(\S+)%s:[ \t]*(\S.*)$" % (_WS, _WS)), ("target", "why")),
    ("answer", re.compile(r"^answer%s(%s)[ \t]*:[ \t]*(\S.*)$" % (_WS, _GD)), ("id", "text")),
    ("drop", re.compile(r"^drop%s(%s)[ \t]*:[ \t]*(\S.*)$" % (_WS, _GD)), ("id", "reason")),
    ("note", re.compile(r"^note%s(\S.*)$" % _WS), ("text",)),
    ("priority", re.compile(r"^priority%s(%s(?:[ \t]*,[ \t]*%s)*)$" % (_WS, _N, _N)), ("ids",)),
    ("limit", re.compile(r"^limit%s(%s)%s([0-9]+)$" % (_WS, _N, _WS)), ("id", "calls")),
    ("allow-fallback", re.compile(r"^allow-fallback%s(%s)%s(archive|browser)$" % (_WS, _N, _WS)),
     ("id", "mode")),
    ("finalize", re.compile(r"^finalize$"), ()),
)

# Commands that request more work and therefore cannot share a file with finalize.
_WORK_COMMANDS = ("accept", "add-source", "answer")

# Commands allowed in an amendment file (dd.py amend); at least one note is required.
AMEND_COMMANDS = ("note", "add-source", "answer", "drop")


class DirectiveError(Exception):
    def __init__(self, errors):
        super().__init__("\n".join(errors))
        self.errors = errors


def _parse_command(text):
    for name, regex, fields in _RULES:
        match = regex.match(text)
        if match:
            cmd = {"cmd": name}
            for field, value in zip(fields, match.groups()):
                if field == "ids":
                    value = [part.strip() for part in value.split(",")]
                elif field == "calls":
                    value = int(value)
                else:
                    value = value.rstrip()
                cmd[field] = value
            return cmd
    return None


def _parse(text, doc, allowed=None):
    """(commands, errors) in file order; allowed limits the command names (None: all)."""
    search_ids = {n["id"] for n in doc.get("next_searches", [])}
    finding_ids = {f["id"] for f in doc.get("findings", [])}
    errors = []
    commands = []
    finalize_line = None
    work_lines = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for part in line.split("|"):
            part = part.strip()
            if not part:
                errors.append("line %d: empty command" % lineno)
                continue
            cmd = _parse_command(part)
            if cmd is None:
                errors.append("line %d: not a directive: %s" % (lineno, part))
                continue
            name = cmd["cmd"]
            if allowed is not None and name not in allowed:
                errors.append("line %d: %s is not allowed in an amendment" % (lineno, name))
                continue
            ids = cmd.get("ids", [cmd["id"]] if "id" in cmd else [])
            for ident in ids:
                known = search_ids if ident.startswith("N") else finding_ids
                if ident not in known:
                    errors.append("line %d: unknown id %s" % (lineno, ident))
            if name == "priority" and len(set(ids)) != len(ids):
                errors.append("line %d: duplicate id in priority" % lineno)
            if name == "limit" and not 1 <= cmd["calls"] <= 20:
                errors.append("line %d: limit calls must be 1..20" % lineno)
            if name == "finalize":
                finalize_line = lineno
            if name in _WORK_COMMANDS:
                work_lines.append(lineno)
            cmd["line"] = lineno
            commands.append(cmd)
    if finalize_line is not None and work_lines:
        errors.append("line %d: finalize cannot be combined with accept/add-source/answer (line %d)"
                      % (finalize_line, work_lines[0]))
    return commands, errors


def parse(text, doc):
    """Return the list of commands in file order; raise DirectiveError listing every error."""
    commands, errors = _parse(text, doc)
    if not commands and not errors:
        errors.append("line 0: no directives found")
    if errors:
        raise DirectiveError(errors)
    return commands


def parse_amendment(text, doc):
    """Like parse, but only AMEND_COMMANDS are allowed and at least one note is required."""
    commands, errors = _parse(text, doc, AMEND_COMMANDS)
    if not any(c["cmd"] == "note" for c in commands):
        errors.append("line 0: an amendment needs at least one note")
    if errors:
        raise DirectiveError(errors)
    return commands


def has_finalize(commands):
    return any(c["cmd"] == "finalize" for c in commands)
