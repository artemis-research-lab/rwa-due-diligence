"""Schema rwa-dd/1.0: the single definition of the DD document, its enums and field limits.

references/schema.md is generated from this module (`dd.py schema-doc`).
"""

SCHEMA_VERSION = "rwa-dd/1.0"
SKILL_VERSION = "0.4.0"

ENUMS = {
    "source_type": (
        "project_site", "project_docs", "legal_doc", "regulator_filing", "regulator_registry",
        "company_registry", "audit_report", "attestation", "proof_of_reserves", "onchain_explorer",
        "rpc_api", "archive", "third_party_research", "news", "web_search", "analyst_input", "other",
    ),
    "origin": ("first_party", "regulator", "registry", "auditor", "onchain", "third_party", "analyst"),
    "fetch": (
        "ok", "js_blocked", "browser_rendered", "pdf", "archived", "http_error", "auth_required",
        "dns_error", "cloudflare", "captcha", "form_required", "timeout", "tool_refused", "offline",
    ),
    "role": (
        "issuer", "spv", "manager", "operator", "platform_operator", "originator", "servicer",
        "custodian", "trustee", "escrow_agent", "collateral_agent", "administrative_agent",
        "administrator", "auditor", "transfer_agent", "registered_agent", "lender", "borrower",
        "insurer", "licensor", "governance_owner", "treasury", "repo_seller", "developer", "other",
    ),
    "relationship_type": (
        "owns", "controls", "issues", "manages", "operates", "originates", "services", "custodies",
        "trustee_for", "administers", "audits", "insures", "lends_to", "licenses_to",
        "repo_counterparty", "guarantees", "other",
    ),
    "lane": ("offchain", "boundary", "onchain"),
    "node_kind": ("investor", "entity", "contract", "pool", "wallet", "multisig", "bank_account", "asset"),
    "edge_kind": ("subscription", "redemption", "yield", "fee", "custody", "conversion", "collateral"),
    "mechanism": (
        "deposit", "mint", "stake", "burn", "drawdown", "repayment", "interest", "distribution", "repo",
        "purchase", "redemption_request", "payout", "conversion", "fee_payment", "pledge",
        "title_transfer", "other",
    ),
    "rail": ("fiat_wire", "stablecoin", "mint", "burn", "bridge", "internal", "unknown"),
    "finding_type": ("gap", "discrepancy", "structural_change"),
    "topic": ("legal", "yield", "flows", "onchain", "redemption", "other"),
    "size_metric": ("tvl", "supply", "nav", "holders", "reserves", "originated", "outstanding", "defaulted"),
    "run_status": ("draft", "final"),
    "claim_status": ("verified", "self_reported", "inferred", "not_found"),
}

# Finding id prefix per finding type.
FINDING_PREFIX = {"gap": "G", "discrepancy": "D", "structural_change": "C"}

# Limits that are not part of a single field.
CLAIM_NOTE_MAX = 200
CLAIM_VALUE_STR_MAX = 300
SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{1,40}$"

# Top-level sections whose claims are legal facts (claim rules, section 3.3).
LEGAL_SECTIONS = ("entities", "relationships", "governing_law", "eligibility")


def id_pattern(*prefixes):
    return r"^(%s)[1-9][0-9]*$" % "|".join(prefixes)


# --------------------------------------------------------------------------- node types

class Node:
    nullable = False

    def describe(self):
        raise NotImplementedError


class Str(Node):
    def __init__(self, max_len, nullable=False):
        self.max_len = max_len
        self.nullable = nullable

    def describe(self):
        return "string <=%d%s" % (self.max_len, " | null" if self.nullable else "")


class Pattern(Node):
    """A string matching regex; kind adds a semantic check (date, timestamp)."""

    def __init__(self, regex, label, nullable=False, kind=None, max_len=None):
        self.regex = regex
        self.label = label
        self.nullable = nullable
        self.kind = kind
        self.max_len = max_len

    def describe(self):
        return "%s%s" % (self.label, " | null" if self.nullable else "")


class Const(Node):
    def __init__(self, value):
        self.value = value

    def describe(self):
        return 'const "%s"' % self.value


class Enum(Node):
    def __init__(self, name):
        self.name = name

    def describe(self):
        return "enum %s" % self.name


class Int(Node):
    def __init__(self, minimum=None, maximum=None):
        self.minimum = minimum
        self.maximum = maximum

    def describe(self):
        if self.maximum is not None:
            return "integer %d..%d" % (self.minimum, self.maximum)
        return "integer >=%d" % self.minimum


class Bool(Node):
    def describe(self):
        return "boolean"


class Claim(Node):
    def describe(self):
        return "Claim"


class Arr(Node):
    def __init__(self, item, min_items=0):
        self.item = item
        self.min_items = min_items

    def describe(self):
        if self.min_items:
            return "array (>=%d)" % self.min_items
        return "array"


class Obj(Node):
    def __init__(self, *fields):
        self.fields = tuple(fields)

    def keys(self):
        return [name for name, _ in self.fields]

    def describe(self):
        return "object"


def Date(nullable=True):
    return Pattern(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", "date YYYY-MM-DD", nullable=nullable, kind="date")


def Timestamp(nullable=False):
    return Pattern(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$",
                   "timestamp YYYY-MM-DDTHH:MM:SSZ", nullable=nullable, kind="timestamp")


def Ref(*prefixes, nullable=False):
    label = "|".join("%s<n>" % p for p in prefixes)
    return Pattern(id_pattern(*prefixes), "id " + label, nullable=nullable)


# --------------------------------------------------------------------------- document

C = Claim()

SOURCE = Obj(
    ("id", Ref("S")),
    ("url", Str(500)),
    ("title", Str(200)),
    ("source_type", Enum("source_type")),
    ("origin", Enum("origin")),
    ("publisher", Ref("E", nullable=True)),
    ("retrieved_at", Timestamp(nullable=True)),
    ("fetch", Enum("fetch")),
    ("excerpt", Str(300)),
    ("excerpt_sha256", Pattern(r"^[0-9a-f]{64}$", "hex64 (lowercase sha256)")),
    ("archived", Bool()),
    ("version_date", Date()),
    ("note", Str(200)),
)

PRODUCT = Obj(
    ("id", Ref("P")),
    ("name", C),
    ("symbol", C),
    ("chains", C),
    ("token_addresses", C),
    ("asset_class", C),
)

DOCUMENT = Obj(
    ("schema_version", Const(SCHEMA_VERSION)),
    ("run", Obj(
        ("run_id", Str(64)),
        ("slug", Pattern(SLUG_PATTERN, "slug " + SLUG_PATTERN)),
        ("root_url", Str(500)),
        ("round", Int(1)),
        ("status", Enum("run_status")),
        ("started_at", Timestamp()),
        ("finalized_at", Timestamp(nullable=True)),
        ("skill_version", Str(20)),
    )),
    ("project", Obj(
        ("name", C),
        ("asset_class", C),
        ("products", Arr(PRODUCT, min_items=1)),
    )),
    ("sources", Arr(SOURCE)),
    ("entities", Arr(Obj(
        ("id", Ref("E")),
        ("legal_name", C),
        ("jurisdiction", C),
        ("entity_type", C),
        ("registration_id", C),
        ("roles", Arr(Enum("role"), min_items=1)),
        ("license_status", C),
        ("licenses", Arr(Obj(
            ("regulator", C),
            ("license_type", C),
            ("license_id", C),
            ("status", C),
        ))),
    ))),
    ("relationships", Arr(Obj(
        ("from", Ref("E")),
        ("to", Ref("E", "P")),
        ("type", Enum("relationship_type")),
        ("claim", C),
    ))),
    ("governing_law", C),
    ("yield", Arr(Obj(
        ("product", Ref("P")),
        ("underlying", Arr(Obj(
            ("description", C),
            ("asset_class", C),
            ("share_pct", C),
            ("location", C),
        ))),
        ("mechanism", C),
        ("gross_yield", C),
        ("net_yield_to_holder", C),
        ("fees", Arr(Obj(
            ("type", C),
            ("rate", C),
            ("recipient", C),
        ))),
        ("distribution", Obj(
            ("method", C),
            ("frequency", C),
        )),
        ("loss_absorption", C),
    ))),
    ("redemption", Arr(Obj(
        ("product", Ref("P")),
        ("mechanism", C),
        ("queue", C),
        ("settlement_time", C),
        ("gating", C),
        ("fees", C),
    ))),
    ("eligibility", Arr(Obj(
        ("product", Ref("P")),
        ("restrictions", C),
    ))),
    ("audits", Arr(Obj(
        ("auditor", C),
        ("scope", C),
        ("date", C),
        ("report_ref", Ref("S", nullable=True)),
    ))),
    ("size", Arr(Obj(
        ("product", Ref("P", nullable=True)),
        ("metric", Enum("size_metric")),
        ("value", C),
        ("as_of", Date()),
    ))),
    ("flows", Obj(
        ("nodes", Arr(Obj(
            ("id", Ref("n")),
            ("label", Str(40)),
            ("lane", Enum("lane")),
            ("kind", Enum("node_kind")),
            ("chain", Str(24, nullable=True)),
            ("ref", Pattern(r"^((E|P)[1-9][0-9]*|[A-Za-z0-9]{1,64})$",
                            "E<n>|P<n>|chain address <alphanumeric, 1..64>", nullable=True)),
        ))),
        ("edges", Arr(Obj(
            ("from", Ref("n")),
            ("to", Ref("n")),
            ("kind", Enum("edge_kind")),
            ("mechanism", Enum("mechanism")),
            ("rail", Enum("rail")),
            ("products", Arr(Ref("P"), min_items=1)),
            ("label", Str(40)),
            ("claim", C),
        ))),
    )),
    ("onchain", Obj(
        ("contracts", Arr(Obj(
            ("chain", Str(24)),
            ("address", Str(64)),
            ("role", C),
            ("source_verified", C),
            ("proxy", C),
            ("control", Obj(
                ("upgrade_admin", C),
                ("role_admins", C),
                ("timelock_delay_s", C),
                ("multisig", Obj(
                    ("address", C),
                    ("threshold", C),
                    ("signers_count", C),
                )),
            )),
        ))),
    )),
    ("history", Arr(Obj(
        ("date", Date()),
        ("change", Str(200)),
        ("evidence", Arr(Ref("S"), min_items=1)),
    ))),
    ("findings", Arr(Obj(
        ("id", Ref("G", "D", "C")),
        ("type", Enum("finding_type")),
        ("topic", Enum("topic")),
        ("blocking", Bool()),
        ("statement", Str(280)),
        ("evidence", Arr(Ref("S"))),
    ))),
    ("open_questions", Arr(Obj(
        ("topic", Enum("topic")),
        ("question", Str(200)),
    ))),
    ("next_searches", Arr(Obj(
        ("id", Ref("N")),
        ("what", Str(120)),
        ("where", Str(120)),
        ("why", Str(120)),
        ("resolves", Arr(Ref("G", "D"))),
        ("est_calls", Int(1, 20)),
    ))),
    ("narrative", Obj(
        ("executive_summary", Str(800)),
    )),
    ("x_unmapped", Arr(Obj(
        ("fact", Str(200)),
        ("evidence", Arr(Ref("S"))),
        ("why_unmapped", Str(120)),
    ))),
)

CLAIM_KEYS = ("value", "status", "evidence", "subject", "note")


# --------------------------------------------------------------------------- helpers

def empty_claim():
    return {"value": None, "status": "not_found", "evidence": [], "subject": None, "note": ""}


def skeleton(node):
    """Default value for a node: claims not_found, arrays empty, scalars null/zero."""
    if isinstance(node, Claim):
        return empty_claim()
    if isinstance(node, Obj):
        return {name: skeleton(child) for name, child in node.fields}
    if isinstance(node, Arr):
        return []
    if isinstance(node, Const):
        return node.value
    if isinstance(node, Bool):
        return False
    if isinstance(node, Int):
        return node.minimum
    if node.nullable:
        return None
    return ""


def order_like_schema(value, node=DOCUMENT):
    """Return value with object keys in schema order; unknown keys keep their order at the end."""
    if isinstance(node, Claim) and isinstance(value, dict):
        known = [k for k in CLAIM_KEYS if k in value]
        return {k: value[k] for k in known + [k for k in value if k not in CLAIM_KEYS]}
    if isinstance(node, Obj) and isinstance(value, dict):
        out = {}
        children = dict(node.fields)
        for name in node.keys():
            if name in value:
                out[name] = order_like_schema(value[name], children[name])
        for name in value:
            if name not in children:
                out[name] = value[name]
        return out
    if isinstance(node, Arr) and isinstance(value, list):
        return [order_like_schema(item, node.item) for item in value]
    return value


def format_path(parts):
    out = ""
    for part in parts:
        if isinstance(part, int):
            out += "[%d]" % part
        elif out:
            out += "." + part
        else:
            out = part
    return out


def iter_claims(doc, node=None, parts=()):
    """Yield (path_parts, claim) for every Claim position in a structurally valid document."""
    node = DOCUMENT if node is None else node
    if isinstance(node, Claim):
        yield parts, doc
    elif isinstance(node, Obj) and isinstance(doc, dict):
        for name, child in node.fields:
            if name in doc:
                yield from iter_claims(doc[name], child, parts + (name,))
    elif isinstance(node, Arr) and isinstance(doc, list):
        for index, item in enumerate(doc):
            yield from iter_claims(item, node.item, parts + (index,))


# --------------------------------------------------------------------------- schema doc

def _doc_tree(node, name, depth, lines):
    pad = "  " * depth
    if isinstance(node, Obj):
        lines.append("%s- `%s`: object" % (pad, name))
        for child_name, child in node.fields:
            _doc_tree(child, child_name, depth + 1, lines)
    elif isinstance(node, Arr):
        item = node.item
        if isinstance(item, Obj):
            lines.append("%s- `%s`: %s of object" % (pad, name, node.describe()))
            for child_name, child in item.fields:
                _doc_tree(child, child_name, depth + 1, lines)
        else:
            lines.append("%s- `%s`: %s of %s" % (pad, name, node.describe(), item.describe()))
    else:
        lines.append("%s- `%s`: %s" % (pad, name, node.describe()))


def schema_doc():
    """Markdown reference for the schema; deterministic and ASCII-only."""
    lines = [
        "# Schema %s" % SCHEMA_VERSION,
        "",
        "Generated by `python3 scripts/dd.py schema-doc` from lib/schema.py. Do not edit by hand.",
        "",
        "## Conventions",
        "",
        "- The schema is closed: every listed key is required and an unknown key anywhere is an error.",
        "- No string anywhere (including inside claim values) may contain a control character.",
        "- `string <=n` is a string of at most n characters. `| null` means null is also allowed.",
        "- Ids are dense from 1 and unique per kind: S (sources), E (entities), P (products),",
        "  n (flow nodes), G/D/C (findings, each prefix counted separately), N (next searches).",
        "- Finding id prefix follows the type: gap=G, discrepancy=D, structural_change=C.",
        "- Every product needs at least one flow edge and one yield entry.",
        "- `history` is sorted by date, nulls last.",
        "- `sources` must equal the source ledger `audit/sources.jsonl`; add sources only with `dd.py add-source`.",
        "",
        "## Claim",
        "",
        "- `value`: any JSON or null; each string inside it <=%d" % CLAIM_VALUE_STR_MAX,
        "- `status`: enum claim_status",
        "- `evidence`: array of id S<n>",
        "- `subject`: id E<n>|P<n> | null",
        "- `note`: string <=%d (may be empty)" % CLAIM_NOTE_MAX,
        "",
        "### Claim rules",
        "",
        "Evidence role of source s for claim c: `self` if s.origin is first_party or s.publisher equals",
        "c.subject; `analyst` if s.origin is analyst; otherwise `independent:<origin>`.",
        "Legal paths: %s." % ", ".join(LEGAL_SECTIONS),
        "",
        "- verified: at least one independent evidence; on legal paths its origin must be",
        "  regulator, registry, auditor or onchain.",
        "- self_reported: at least one self evidence.",
        "- inferred: at least one evidence and a non-empty note.",
        "- verified, self_reported and inferred: value is not null.",
        "- not_found: value is null; if evidence is non-empty the note must be non-empty.",
        "- subject references an existing entity or product, or is null.",
        "",
        "## Enums",
        "",
    ]
    for name in sorted(ENUMS):
        lines.append("- `%s`: %s" % (name, ", ".join("`%s`" % v for v in ENUMS[name])))
    lines += ["", "## Document", ""]
    for name, child in DOCUMENT.fields:
        _doc_tree(child, name, 0, lines)
    return "\n".join(lines) + "\n"
