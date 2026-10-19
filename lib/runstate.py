"""Run directory contract (D8), path safety and the round state machine (section 3.5).

This module and lib/ledger.py are the only writers of <root>/<slug>/.
"""

import re
from pathlib import Path

from lib import directives, flow, ledger, migrate, render_md, review, schema, validate
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
# figures maps "T<n>-<view>" -> sanitized SVG text and may be empty; rejected is a set of N ids.
RENDERERS = [("report.md", render_md.render)]

FLOW_VIEWS = schema.ENUMS["flow_view"]


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

    def flow_output(self, key):
        """Diagram output for key T<n>-<view>."""
        return self.output("flow-%s.svg" % key)

    def flow_outputs(self):
        """Existing flow diagram outputs, by strategy id then view order settlement, claim, repayment."""
        pattern = re.compile(r"^%s\.flow-(T[1-9][0-9]*)-(settlement|claim|repayment)\.svg$" % re.escape(self.slug))
        found = {}
        for path in self.dir.glob("%s.flow-T*.svg" % self.slug):
            match = pattern.match(path.name)
            if match:
                found[(id_key(match.group(1)), FLOW_VIEWS.index(match.group(2)))] = path
        return [found[key] for key in sorted(found)]

    def legacy_outputs(self):
        """Final outputs of runs made before v0.5.0 (HTML report, one diagram per product)."""
        pattern = re.compile(r"^%s\.flow-P[1-9][0-9]*\.svg$" % re.escape(self.slug))
        flows = sorted(p for p in self.dir.glob("%s.flow-P*.svg" % self.slug) if pattern.match(p.name))
        return [p for p in [self.output("report.html")] + flows if p.exists()]

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

def _new_run(slug, url, clock, seeded_from=None):
    started = ledger.format_ts(clock())
    run_id = "%s-%s" % (slug, started.replace("-", "").replace(":", ""))
    return {"run_id": run_id, "slug": slug, "root_url": url, "round": 1, "status": "draft",
            "started_at": started, "finalized_at": None, "skill_version": schema.SKILL_VERSION,
            "seeded_from": seeded_from}


def _skeleton(slug, url, clock):
    doc = schema.skeleton(schema.DOCUMENT)
    doc["run"] = _new_run(slug, url, clock)
    product = schema.skeleton(schema.PRODUCT)
    product["id"] = "P1"
    doc["project"]["products"] = [product]
    strategy = schema.skeleton(schema.STRATEGY)
    strategy.update({"id": "T1", "products": ["P1"]})
    doc["strategies"] = [strategy]
    rights = schema.skeleton(schema.HOLDER_RIGHTS)
    rights["product"] = "P1"
    doc["holder_rights"] = [rights]
    errors = validate.structural_errors(doc)
    if errors:
        raise InvalidError(sorted(set(errors)))
    return doc, doc["run"]["run_id"]


def _archive_run(project, state):
    """Move the run's outputs and audit/ to archive/<run_id>/; returns [(src, dst), ...] for a rollback."""
    dest = project.archive / state["run_id"]
    if dest.exists():
        raise ContractError("archive %s already exists" % dest)
    moved = []
    for path in project.outputs() + project.legacy_outputs():
        if path.exists():
            project.move(path, dest / path.name)
            moved.append((path, dest / path.name))
    project.move(project.audit, dest / "audit")
    moved.append((project.audit, dest / "audit"))
    return moved


def _rollback(project, moved, archive_existed):
    """Undo _archive_run: move everything back and remove the directories it created."""
    for src, dst in reversed(moved):
        project.move(dst, src)
    created = [moved[-1][1].parent] + ([] if archive_existed else [project.archive])
    for path in created:
        path = project.safe(path)
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def _start_layout(project):
    for sub in SCRATCH_DIRS:
        project.mkdir(project.scratch / sub)
    project.mkdir(project.rounds)


def _seed_version(old):
    """Schema version of the record to seed from; ContractError unless it is 1.0 or 2.0."""
    version = old.get("schema_version") if isinstance(old, dict) else None
    if version not in (migrate.FROM_VERSION, schema.SCHEMA_VERSION):
        raise ContractError("cannot seed from schema version %r (supported: %s, %s)"
                            % (version, migrate.FROM_VERSION, schema.SCHEMA_VERSION))
    return version


def _seeded_doc(old, run):
    """Working document of a seeded run (4.2 step 3)."""
    if _seed_version(old) == migrate.FROM_VERSION:
        return migrate.convert(old, run)
    return schema.order_like_schema(dict(old, run=run, next_searches=[]))


def seed(root, slug, url, clock=ledger.system_clock):
    """init --seed-from (4.2): archive the existing run and start a new one from its record and ledger."""
    project = Project(root, slug)
    if not project.state_file.is_file():
        raise ContractError("no run for slug %s under %s to seed from" % (slug, project.root))
    state = load_state(project)
    old = load_work(project)
    run = _new_run(slug, url, clock, seeded_from=state["run_id"])
    _seed_version(old)  # refuses unknown versions before anything moves
    archive_existed = project.archive.exists()
    moved = _archive_run(project, state)
    try:
        ledger_bytes = (project.archive / state["run_id"] / "audit" / "sources.jsonl").read_bytes()
        try:
            doc = _seeded_doc(old, run)
        except (KeyError, TypeError, AttributeError, IndexError) as exc:
            raise InvalidError(["seed: %s record cannot be converted (%s: %s)"
                                % (old.get("schema_version"), type(exc).__name__, exc)])
        errors = validate.structural_errors(doc)
        if not errors:
            sources = ledger.read_ledger(project.archive / state["run_id"] / "audit" / "sources.jsonl")
            errors = validate.validate_document(doc, sources)
        if errors:
            raise InvalidError(sorted(set(errors)))
    except Exception:
        _rollback(project, moved, archive_existed)
        raise
    _start_layout(project)
    project.write_bytes(project.ledger_file, ledger_bytes)
    save_work(project, doc)
    save_state(project, {"slug": slug, "run_id": run["run_id"], "round": 1, "phase": PHASE_RESEARCH,
                         "status": "draft"})
    return {"project_dir": str(project.dir), "run_id": run["run_id"], "work_file": str(project.work_file),
            "seeded_from": state["run_id"], "sources": len(doc["sources"])}


def init(root, slug, url, clock=ledger.system_clock, new_run=False):
    project = Project(root, slug)
    doc, run_id = _skeleton(slug, url, clock)
    if project.state_file.is_file():
        state = load_state(project)
        if not new_run:
            if state.get("status") == "final":
                raise ContractError('run %s is final; use "dd.py amend" to correct it, --seed-from to re-map it or'
                                    ' --new-run to archive it and start again' % state.get("run_id"))
            raise ContractError('run exists (phase %s); use "dd.py status" to inspect or --new-run to archive it'
                                ' and start again' % state.get("phase"))
        _archive_run(project, state)
    elif project.audit.exists():
        raise ContractError("%s exists without state.json" % project.audit)

    _start_layout(project)
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
    for key, svg in figures.items():
        outputs.append(str(project.write_text(draft / project.flow_output(key).name, svg)))
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
                          ("entities", ("entities",)), ("strategies", ("strategies",)),
                          ("interfaces", ("interfaces",)), ("flow_edges", ("flows", "edges")),
                          ("findings", ("findings",)), ("next_searches", ("next_searches",))):
            value = doc
            for part in path:
                value = value.get(part, []) if isinstance(value, dict) else []
            counts[key] = len(value) if isinstance(value, list) else 0
    except InvalidError as exc:
        errors = exc.errors
    return {"state": state, "counts": counts, "valid": not errors, "errors": len(errors)}


def render_figures(doc):
    """Sanitized SVG per "T<n>-<view>" key; DependencyError when d2 is missing or not the pinned version."""
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
    for key, svg in figures.items():
        outputs.append(project.write_text(project.flow_output(key), svg))
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
    for path in project.outputs() + project.legacy_outputs():
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
