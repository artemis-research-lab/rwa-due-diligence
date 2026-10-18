"""Run directory contract (D8), path safety and the round state machine (section 3.5).

This module and lib/ledger.py are the only writers of <root>/<slug>/.
"""

import re
from pathlib import Path

from lib import directives, flow, ledger, render_html, render_md, review, schema, validate
from lib.textutil import dump_json, id_key, load_json_text

PHASE_RESEARCH = "research"
PHASE_AWAITING = "awaiting_directives"
PHASE_READY = "ready_to_finalize"
PHASE_FINAL = "final"

SCRATCH_DIRS = ("raw", "text", "draft", "logs")


class ContractError(Exception):
    """Path or state contract violation (CLI exit 3)."""


class InvalidError(Exception):
    """Invalid document or directives (CLI exit 2)."""

    def __init__(self, errors):
        super().__init__("\n".join(errors))
        self.errors = list(errors)


# Renderers that finalize runs: (output suffix, function(doc, rounds, figures, rejected=()) -> text);
# figures maps product id -> sanitized SVG text and may be empty; rejected is a set of N ids.
RENDERERS = [("report.md", render_md.render), ("report.html", render_html.render)]


def check_slug(slug):
    if not isinstance(slug, str) or not re.match(schema.SLUG_PATTERN, slug):
        raise ContractError("invalid slug %r: must match %s" % (slug, schema.SLUG_PATTERN))
    return slug


class Project:
    """Paths of one project directory; every write goes through safe()."""

    def __init__(self, root, slug):
        self.slug = check_slug(slug)
        self.root = Path(root).resolve()
        self.dir = self.root / slug
        if self.dir.is_symlink():
            raise ContractError("project directory %s is a symlink" % self.dir)
        self.audit = self.dir / "audit"
        self.state_file = self.audit / "state.json"
        self.work_file = self.audit / "dd.work.json"
        self.ledger_file = self.audit / "sources.jsonl"
        self.rounds = self.audit / "rounds"
        self.scratch = self.dir / ".scratch"
        self.archive = self.dir / "archive"

    def output(self, suffix):
        return self.dir / ("%s.%s" % (self.slug, suffix))

    def flow_output(self, product_id):
        return self.output("flow-%s.svg" % product_id)

    def flow_outputs(self):
        """Existing flow diagram outputs, by product id."""
        pattern = re.compile(r"^%s\.flow-(P[1-9][0-9]*)\.svg$" % re.escape(self.slug))
        found = {}
        for path in self.dir.glob("%s.flow-P*.svg" % self.slug):
            match = pattern.match(path.name)
            if match:
                found[match.group(1)] = path
        return [found[pid] for pid in sorted(found, key=id_key)]

    def outputs(self):
        return ([self.output("dd.json")] + [self.output(suffix) for suffix, _ in RENDERERS]
                + self.flow_outputs())

    def round_dir(self, k):
        return self.rounds / ("r%d" % k)

    def safe(self, path):
        """Resolve path (following symlinks) and require it to lie inside the project directory."""
        resolved = Path(path).resolve()
        base = self.dir.resolve()
        if resolved != base and base not in resolved.parents:
            raise ContractError("path %s escapes the project directory %s" % (path, base))
        return resolved

    def mkdir(self, path):
        self.safe(path).mkdir(parents=True, exist_ok=True)

    def write_bytes(self, path, data):
        target = self.safe(path)
        self.safe(target.parent).mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def write_text(self, path, text):
        return self.write_bytes(path, text.encode("utf-8"))

    def write_json(self, path, value):
        return self.write_text(path, dump_json(value))

    def append_source(self, source):
        ledger.append_line(self.safe(self.ledger_file), source)

    def move(self, src, dst):
        self.safe(dst.parent).mkdir(parents=True, exist_ok=True)
        self.safe(src).rename(self.safe(dst))


# --------------------------------------------------------------------------- loading

def open_project(root, slug):
    project = Project(root, slug)
    if not project.state_file.is_file():
        raise ContractError("no run for slug %s under %s (run init first)" % (slug, project.root))
    return project


def load_state(project):
    return load_json_text(project.state_file.read_bytes().decode("utf-8"))


def save_state(project, state):
    project.write_json(project.state_file, state)


def load_work(project):
    try:
        return load_json_text(project.work_file.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidError(["audit/dd.work.json: not valid JSON: %s" % exc])


def save_work(project, doc):
    project.write_json(project.work_file, schema.order_like_schema(doc))


def check_work(project, doc=None):
    doc = load_work(project) if doc is None else doc
    return validate.validate_document(doc, ledger.read_ledger(project.ledger_file))


def round_records(project, upto):
    """[(heading, text), ...] for rounds 1..upto: an amendment that reopened round k precedes round k."""
    out = []
    for k in range(1, upto + 1):
        rdir = project.round_dir(k)
        amend_txt = rdir / "amend.txt"
        if amend_txt.is_file():
            record = load_json_text((rdir / "amend.json").read_bytes().decode("utf-8"))
            out.append(("Amendment %d (reopens round %d)" % (record["amendment"], k),
                        amend_txt.read_bytes().decode("utf-8", errors="replace")))
        path = rdir / "directives.txt"
        if path.is_file():
            out.append(("Round %d" % k, path.read_bytes().decode("utf-8", errors="replace")))
    return out


def rejected_ids(project, k):
    """N ids rejected in round k's directives (the round holding the finalize directive)."""
    path = project.round_dir(k) / "directives.json"
    if not path.is_file():
        return set()
    commands = load_json_text(path.read_bytes().decode("utf-8"))
    return {c["id"] for c in commands if c.get("cmd") == "reject"}


# --------------------------------------------------------------------------- commands

def _skeleton(slug, url, clock):
    started = ledger.format_ts(clock())
    run_id = "%s-%s" % (slug, started.replace("-", "").replace(":", ""))
    doc = schema.skeleton(schema.DOCUMENT)
    doc["run"] = {"run_id": run_id, "slug": slug, "root_url": url, "round": 1, "status": "draft",
                  "started_at": started, "finalized_at": None, "skill_version": schema.SKILL_VERSION}
    product = schema.skeleton(schema.PRODUCT)
    product["id"] = "P1"
    doc["project"]["products"] = [product]
    errors = validate.structural_errors(doc)
    if errors:
        raise InvalidError(sorted(set(errors)))
    return doc, run_id


def init(root, slug, url, clock=ledger.system_clock, new_run=False):
    project = Project(root, slug)
    doc, run_id = _skeleton(slug, url, clock)
    if project.state_file.is_file():
        state = load_state(project)
        if not new_run:
            if state.get("status") == "final":
                raise ContractError('run %s is final; use "dd.py amend" to correct it or --new-run to archive it and'
                                    ' start again' % state.get("run_id"))
            raise ContractError('run exists (phase %s); use "dd.py status" to inspect or --new-run to archive it'
                                ' and start again' % state.get("phase"))
        dest = project.archive / state["run_id"]
        if dest.exists():
            raise ContractError("archive %s already exists" % dest)
        for path in project.outputs() + [project.output("report.html")]:
            if path.exists():
                project.move(path, dest / path.name)
        project.move(project.audit, dest / "audit")
    elif project.audit.exists():
        raise ContractError("%s exists without state.json" % project.audit)

    for sub in SCRATCH_DIRS:
        project.mkdir(project.scratch / sub)
    project.mkdir(project.rounds)
    project.write_bytes(project.ledger_file, b"")
    save_work(project, doc)
    state = {"slug": slug, "run_id": run_id, "round": 1, "phase": PHASE_RESEARCH, "status": "draft"}
    save_state(project, state)
    return {"project_dir": str(project.dir), "run_id": run_id, "work_file": str(project.work_file)}


def add_source(root, slug, clock=ledger.system_clock, **fields):
    project = open_project(root, slug)
    state = load_state(project)
    if state["phase"] != PHASE_RESEARCH:
        raise ContractError("add-source requires phase research (current: %s)" % state["phase"])
    doc = load_work(project)
    if not isinstance(doc.get("sources"), list):
        raise InvalidError(["sources: must be an array"])
    existing = ledger.read_ledger(project.ledger_file)
    try:
        source = ledger.make_source(len(existing) + 1, clock=clock, **fields)
    except ValueError as exc:
        raise InvalidError(exc.args[0])
    project.append_source(source)
    doc["sources"].append(source)
    save_work(project, doc)
    return source


def check(root, slug):
    project = open_project(root, slug)
    return check_work(project)


def make_review(root, slug):
    project = open_project(root, slug)
    state = load_state(project)
    if state["phase"] not in (PHASE_RESEARCH, PHASE_AWAITING):
        raise ContractError("review requires phase research or awaiting_directives (current: %s)"
                            % state["phase"])
    doc = load_work(project)
    errors = check_work(project, doc)
    if errors:
        raise InvalidError(errors)
    k = state["round"]
    path = project.write_text(project.round_dir(k) / "review.md", review.render(doc, k))
    state["phase"] = PHASE_AWAITING
    save_state(project, state)
    return {"review": str(path), "round": k}


def apply_directives(root, slug, file_path):
    project = open_project(root, slug)
    state = load_state(project)
    if state["phase"] != PHASE_AWAITING:
        raise ContractError("directives requires phase awaiting_directives (current: %s)" % state["phase"])
    raw = Path(file_path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidError(["line 0: directives file is not UTF-8"])
    doc = load_work(project)
    try:
        commands = directives.parse(text, doc)
    except directives.DirectiveError as exc:
        raise InvalidError(exc.errors)
    k = state["round"]
    rdir = project.round_dir(k)
    project.write_bytes(rdir / "directives.txt", raw)
    project.write_json(rdir / "directives.json", commands)
    if directives.has_finalize(commands):
        state["phase"] = PHASE_READY
    else:
        state["round"] = k + 1
        state["phase"] = PHASE_RESEARCH
        doc["run"]["round"] = k + 1
        save_work(project, doc)
    save_state(project, state)
    return {"round": state["round"], "phase": state["phase"], "commands": len(commands)}


def render_draft(root, slug):
    project = open_project(root, slug)
    state = load_state(project)
    doc = load_work(project)
    errors = validate.structural_errors(doc)
    if errors:
        raise InvalidError(sorted(set(errors)))
    warnings = []
    try:
        figures = render_figures(doc)
    except flow.DependencyError:
        figures = {}
        warnings.append("d2 %s not found: diagrams omitted" % flow.D2_VERSION)
    draft = project.scratch / "draft"
    outputs = []
    for suffix, fn in RENDERERS:
        outputs.append(str(project.write_text(draft / ("%s.%s" % (slug, suffix)),
                                              fn(doc, round_records(project, state["round"]), figures))))
    for pid, svg in figures.items():
        outputs.append(str(project.write_text(draft / project.flow_output(pid).name, svg)))
    result = {"outputs": outputs}
    if warnings:
        result["warnings"] = warnings
    return result


def status(root, slug):
    project = open_project(root, slug)
    state = load_state(project)
    counts = {"ledger_sources": len(ledger.read_ledger(project.ledger_file))}
    try:
        doc = load_work(project)
        errors = check_work(project, doc)
        for key, path in (("products", ("project", "products")), ("sources", ("sources",)),
                          ("entities", ("entities",)), ("flow_edges", ("flows", "edges")),
                          ("findings", ("findings",)), ("next_searches", ("next_searches",))):
            value = doc
            for part in path:
                value = value.get(part, []) if isinstance(value, dict) else []
            counts[key] = len(value) if isinstance(value, list) else 0
    except InvalidError as exc:
        errors = exc.errors
    return {"state": state, "counts": counts, "valid": not errors, "errors": len(errors)}


def render_figures(doc):
    """Sanitized SVG per product; DependencyError when d2 is missing or not the pinned version."""
    d2_path = flow.find_d2()
    if d2_path is None:
        raise flow.DependencyError("d2 %s required, found none on PATH" % flow.D2_VERSION)
    flow.check_d2(d2_path)
    return flow.render_all(doc, d2_path)


def finalize(root, slug, clock=ledger.system_clock):
    project = open_project(root, slug)
    state = load_state(project)
    if state["phase"] != PHASE_READY:
        raise ContractError("finalize requires a finalize directive (current phase: %s)" % state["phase"])
    doc = load_work(project)
    if isinstance(doc.get("run"), dict):
        doc["run"]["status"] = "final"
        doc["run"]["finalized_at"] = ledger.format_ts(clock())
    errors = check_work(project, doc)
    if errors:
        raise InvalidError(errors)
    doc = schema.order_like_schema(doc)
    rounds = round_records(project, state["round"])
    rejected = rejected_ids(project, state["round"])
    figures = render_figures(doc)  # d2 is mandatory here: fails before anything is written
    outputs = [project.write_json(project.output("dd.json"), doc)]
    for suffix, fn in RENDERERS:
        outputs.append(project.write_text(project.output(suffix), fn(doc, rounds, figures, rejected)))
    for pid, svg in figures.items():
        outputs.append(project.write_text(project.flow_output(pid), svg))
    save_work(project, doc)
    state["status"] = "final"
    state["phase"] = PHASE_FINAL
    save_state(project, state)
    return {"project_dir": str(project.safe(project.dir)), "outputs": [str(p) for p in outputs],
            "audit_dir": str(project.safe(project.audit)), "scratch_dir": str(project.safe(project.scratch)),
            "rounds": state["round"]}


def amend(root, slug, file_path):
    """Reopen a final run for one more research round (section 1 of the v0.4.1 patch)."""
    project = open_project(root, slug)
    state = load_state(project)
    if state["phase"] != PHASE_FINAL:
        raise ContractError("amend requires a final run (current phase: %s)" % state["phase"])
    m = state.get("amendment", 0)
    n = m + 1
    dest = project.archive / ("%s.v%d" % (state["run_id"], m))
    if dest.exists():
        raise ContractError("archive %s already exists" % dest)
    raw = Path(file_path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidError(["line 0: amendment file is not UTF-8"])
    doc = load_work(project)
    try:
        commands = directives.parse_amendment(text, doc)
    except directives.DirectiveError as exc:
        raise InvalidError(exc.errors)

    k = state["round"]
    project.mkdir(dest)
    for path in project.outputs():
        if path.exists():
            project.move(path, dest / path.name)
    rdir = project.round_dir(k + 1)
    project.write_bytes(rdir / "amend.txt", raw)
    project.write_json(rdir / "amend.json", {"amendment": n, "reopens_round": k + 1, "commands": commands})
    doc["run"]["round"] = k + 1
    doc["run"]["status"] = "draft"
    doc["run"]["finalized_at"] = None
    doc["run"]["skill_version"] = schema.SKILL_VERSION
    save_work(project, doc)
    state.update({"round": k + 1, "phase": PHASE_RESEARCH, "status": "draft", "amendment": n})
    save_state(project, state)
    return {"amendment": n, "round": k + 1, "phase": PHASE_RESEARCH, "archived_to": str(project.safe(dest)),
            "commands": len(commands)}
