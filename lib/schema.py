"""Schema rwa-dd/2.1: the single definition of the DD document, its enums and field limits.

references/schema.md is generated from this module (`dd.py schema-doc`).
"""

SCHEMA_VERSION = "rwa-dd/2.1"
SKILL_VERSION = "0.6.0"

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
        "insurer", "licensor", "governance_owner", "treasury", "repo_seller", "developer",
        "vault", "token_issuer", "protocol_operator", "holder_counterparty", "credit_manager",
        "lender_of_record", "security_agent", "financing_recipient", "receivables_seller",
        "asset_holding_spv", "guarantor", "contractual_obligor", "cash_flow_source", "offtaker_customer",
        "loan_purchaser", "protection_provider", "reserve_assets", "other",
    ),
    "layer": ("L1", "L2", "L3", "L3-O"),
    "interface_kind": ("holder_L1", "L1_L2", "L2_L3", "within_L1", "within_L2", "within_L3", "L3_L3O",
                       "sleeve_holding", "reserve_lookthrough", "asset_sale"),
    "route_code": ("POOL", "FUND", "DIRECT", "WRAPPER"),
    "method_code": ("DL", "DI", "AP", "PI", "REPO", "PT", "OTHER"),
    "legal_class": ("DL", "DI", "AP", "PI", "FI", "EI", "PROTOCOL_ENTITLEMENT", "OTHER"),
    "component": ("CORE_CREDIT", "LIQUIDITY_SLEEVE", "DEFI_LENDING"),
    "amount_basis": ("GROSS_FUNDED", "COMMITMENT", "LOOKTHROUGH", "RESERVE", "SALE_PROCEEDS"),
    "entity_class": ("legal_person", "contract_or_pool", "program", "obligor_group", "unknown"),
    "support_type": ("CREDIT_ENHANCEMENT", "YIELD_SUPPORT"),
    "security": ("secured", "unsecured", "partially_secured"),
    "look_through": ("none", "via_security_trust", "via_spv", "direct_claim", "unresolved"),
    "business_type": ("private_credit", "trade_finance_pt", "mixed", "other"),
    "flow_view": ("settlement", "claim", "repayment"),
    "evidence_flag": ("CONFIRMED", "SELF_REPORTED", "THIRD_PARTY_REPORTED", "INFERRED", "UNRESOLVED", "CONFLICTING"),
    "question_code": (
        "A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "C1", "C2", "C3", "C4", "C5", "C6", "C7",
        "D1", "D2", "D3", "D4", "D5", "E1", "E2", "E3", "E4", "F1", "F2", "F3",
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
    "finding_type": ("gap", "discrepancy", "structural_change", "scope_unresolved"),
    "topic": ("legal", "yield", "flows", "onchain", "redemption", "credit", "holder_rights", "business", "other"),
    "size_metric": ("tvl", "supply", "nav", "holders", "reserves", "originated", "outstanding", "defaulted"),
    "run_status": ("draft", "final"),
    "claim_status": ("verified", "self_reported", "third_party_reported", "inferred", "not_found"),
}

# Finding id prefix per finding type.
FINDING_PREFIX = {"gap": "G", "discrepancy": "D", "structural_change": "C", "scope_unresolved": "U"}

# Limits that are not part of a single field.
CLAIM_NOTE_MAX = 200
CLAIM_VALUE_STR_MAX = 300
SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{1,40}$"

# Top-level sections whose claims are legal facts (claim rules, section 3.3).
LEGAL_SECTIONS = ("entities", "interfaces", "holder_rights", "supports", "eligibility")

# Scope note of a discrepancy carried over from rwa-dd/2.0 (migration, review packet, finalize).
MIGRATED_SCOPE_NOTE = "unchecked (migrated from rwa-dd/2.0)"

# Coded claims (D39): (section, field) -> (enum, shape); shape "one" = one enum string, "list" = non-empty list
# of enum strings without duplicates, "strings" = non-empty ordered list of strings, "number" = an int or float
# >= 0 that is not a boolean.
CODED_CLAIMS = {
    ("strategies", "business_type"): ("business_type", "one"),
    ("interfaces", "route"): ("route_code", "one"),
    ("interfaces", "method"): ("method_code", "list"),
    ("interfaces", "legal_class"): ("legal_class", "one"),
    ("interfaces", "security"): ("security", "one"),
    ("holder_rights", "look_through"): ("look_through", "one"),
    ("strategies", "loss_waterfall"): (None, "strings"),
    ("interfaces", "amount"): (None, "number"),
}

SUBJECT_PATTERN = r"^(E|P|T|X|Z)[1-9][0-9]*(\.[a-z][a-z0-9_]*){0,3}$"


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
    def __init__(self, name, nullable=False):
        self.name = name
        self.nullable = nullable

    def describe(self):
        return "enum %s%s" % (self.name, " | null" if self.nullable else "")


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

STRATEGY = Obj(
    ("id", Ref("T")),
    ("products", Arr(Ref("P"), min_items=1)),
    ("name", Str(80)),
    ("component", Enum("component")),
    ("business_type", C),
    ("sublayers", Str(200)),
    ("l3_business", Obj(
        ("description", C),
        ("revenue_model", C),
        ("cash_generation", C),
        ("collections_control", C),
        ("concentration", C),
        ("performance", C),
        ("operating_history", C),
    )),
    ("default_path", Obj(
        ("events_of_default", C),
        ("enforcement", C),
        ("loss_waterfall", C),
        ("recovery_history", C),
    )),
)

INTERFACE = Obj(
    ("id", Ref("X")),
    ("strategy", Ref("T")),
    ("kind", Enum("interface_kind")),
    ("from", Ref("E", "P")),
    ("to", Ref("E")),
    ("route", C),
    ("method", C),
    ("legal_class", C),
    ("instrument", C),
    ("currency", C),
    ("counterparty", C),
    ("governing_law", C),
    ("claim_holder", C),
    ("terms", C),
    ("security", C),
    ("collateral", C),
    ("perfection", C),
    ("enforcement", C),
    ("recourse", C),
    ("alternative", Obj(
        ("group", Pattern(r"^A[1-9][0-9]*$", "A<n>", nullable=True)),
        ("option", Pattern(r"^[a-z]$", "letter a-z", nullable=True)),
    )),
    ("amount", C),
    ("amount_basis", Enum("amount_basis", nullable=True)),
    ("supply_concentration", C),
    ("title_transfer", C),
    ("servicing", C),
    ("residual_exposure", C),
    ("as_of", Date()),
)

SUPPORT = Obj(
    ("id", Ref("Z")),
    ("type", Enum("support_type")),
    ("strategies", Arr(Ref("T"), min_items=1)),
    ("provider", Ref("E")),
    ("beneficiary", Ref("E", "P", nullable=True)),
    ("covered_exposure", C),
    ("trigger", C),
    ("coverage", C),
    ("exclusions", C),
    ("priority", C),
    ("enforceability", C),
    ("governing_law", C),
    ("holder_recourse", C),
)

HOLDER_RIGHTS = Obj(
    ("product", Ref("P")),
    ("instrument_nature", C),
    ("claim_against", C),
    ("look_through", C),
    ("recourse", C),
    ("governing_law", C),
    ("forum", C),
    ("insolvency_protection", C),
    ("disclaimers", C),
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
        ("seeded_from", Str(64, nullable=True)),
    )),
    ("project", Obj(
        ("name", C),
        ("asset_class", C),
        ("products", Arr(PRODUCT, min_items=1)),
    )),
    ("strategies", Arr(STRATEGY, min_items=1)),
    ("sources", Arr(SOURCE)),
    ("entities", Arr(Obj(
        ("id", Ref("E")),
        ("entity_class", Enum("entity_class")),
        ("legal_name", C),
        ("jurisdiction", C),
        ("entity_type", C),
        ("registration_id", C),
        ("functions", Arr(Obj(
            ("layer", Enum("layer", nullable=True)),
            ("role", Enum("role")),
            ("strategy", Ref("T", nullable=True)),
            ("evidence", Arr(Ref("S"), min_items=1)),
        ))),
        ("license_status", C),
        ("licenses", Arr(Obj(
            ("regulator", C),
            ("license_type", C),
            ("license_id", C),
            ("status", C),
        ))),
    ))),
    ("interfaces", Arr(INTERFACE)),
    ("holder_rights", Arr(HOLDER_RIGHTS)),
    ("supports", Arr(SUPPORT)),
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
            ("layer", Pattern(r"^(L1|L2|L3|L3-O)$", "L1|L2|L3|L3-O", nullable=True)),
        ))),
        ("edges", Arr(Obj(
            ("from", Ref("n")),
            ("to", Ref("n")),
            ("kind", Enum("edge_kind")),
            ("mechanism", Enum("mechanism")),
            ("rail", Enum("rail")),
            ("view", Enum("flow_view")),
            ("strategies", Arr(Ref("T"), min_items=1)),
            ("interface", Ref("X", nullable=True)),
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
        ("id", Ref("G", "D", "C", "U")),
        ("type", Enum("finding_type")),
        ("topic", Enum("topic")),
        ("blocking", Bool()),
        ("material", Bool()),
        ("statement", Str(280)),
        ("scope_note", Str(200)),
        ("evidence", Arr(Ref("S"))),
        ("subjects", Arr(Pattern(SUBJECT_PATTERN, "subject path (E|P|T|X|Z)<n>[.field]{0,3}"))),
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
    ("issuer_requests", Arr(Obj(
        ("id", Ref("Q")),
        ("request", Str(200)),
        ("why", Str(200)),
        ("answers", Arr(Enum("question_code"), min_items=1)),
        ("priority", Int(1, 3)),
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
        "- Ids are dense from 1 and unique per kind: S (sources), E (entities), P (products), T (strategies),",
        "  X (interfaces), Z (supports), n (flow nodes), G/D/C/U (findings, each prefix counted separately),",
        "  N (next searches), Q (issuer requests).",
        "- Finding id prefix follows the type: gap=G, discrepancy=D, structural_change=C, scope_unresolved=U.",
        "- A discrepancy needs a non-empty `scope_note` (why both statements concern the same fact, timeframe and",
        "  scope). A record migrated from rwa-dd/2.0 carries the placeholder `%s`;" % MIGRATED_SCOPE_NOTE,
        "  finalize refuses it.",
        "- Every product is in at least one strategy, has exactly one holder_rights entry and at least one yield",
        "  entry. Every strategy with component CORE_CREDIT or DEFI_LENDING has at least one flow edge with view",
        "  settlement (LIQUIDITY_SLEEVE is exempt).",
        "- Interface `from` is a product id (its token holders) exactly when kind is holder_L1; otherwise an entity;",
        "  `from` and `to` differ.",
        "- `entities[].functions[].layer` may be null only for the roles issuer, loan_purchaser,",
        "  protection_provider, reserve_assets, auditor and other.",
        "- `interfaces[].alternative`: `group` and `option` are both null or both set; a group has at least two",
        "  distinct options and all its interfaces belong to one strategy.",
        "- `interfaces[].amount_basis` is required when `interfaces[].amount` has a value.",
        "- `supports[]`: `strategies` are T ids, `provider` an E id, `beneficiary` an E or P id or null.",
        "- `findings[].subjects` name claims by subject path (see Evidence flags); the leading id must exist.",
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
        "- verified: at least one independent evidence and no analyst evidence; on legal paths its origin must be",
        "  regulator, registry, auditor or onchain.",
        "- self_reported: at least one self evidence.",
        "- third_party_reported: at least one independent evidence of any origin (allowed on legal paths; it is",
        "  not verification).",
        "- inferred: at least one evidence and a non-empty note.",
        "- verified, self_reported, third_party_reported and inferred: value is not null.",
        "- not_found: value is null; if evidence is non-empty the note must be non-empty.",
        "- subject references an existing entity or product, or is null.",
        "",
        "### Coded claims",
        "",
        "When the value is not null:",
        "",
        "- `strategies[].business_type`, `interfaces[].route`, `interfaces[].legal_class`, `interfaces[].security`",
        "  and `holder_rights[].look_through`: one string from enum business_type, route_code, legal_class, security",
        "  and look_through respectively.",
        "- `interfaces[].method`: a non-empty list of method_code strings without duplicates.",
        "- `strategies[].default_path.loss_waterfall`: a non-empty ordered list of strings (the first absorbs",
        "  losses first).",
        "- `interfaces[].amount`: a number >= 0 (an integer or a float, not a boolean).",
        "",
        "Kind constraints: these interface claims must be not_found with empty evidence unless the kind matches:",
        "`route` and `supply_concentration` (L1_L2); `method` (L2_L3 or L3_L3O); `title_transfer`, `servicing` and",
        "`residual_exposure` (asset_sale).",
        "",
        "### Evidence flags (derived, never stored)",
        "",
        "- Subject path of a claim: the id of the nearest enclosing object that has an `id` in E, P, T, X or Z,",
        "  followed by the field names below it, indexes dropped (for example `X3.security`,",
        "  `T1.default_path.loss_waterfall`, `E2.legal_name`, `Z1.coverage`). Holder-rights claims take their",
        "  product's id: `P<n>.holder_rights.<field>`. Claims outside such objects have none.",
        "- A claim is conflicted when a discrepancy finding's `subjects` contains its subject path or a prefix of it",
        "  that ends at a field boundary. scope_unresolved findings never make a claim conflicted.",
        "- Six flags: CONFLICTING if conflicted; otherwise verified gives CONFIRMED, self_reported SELF_REPORTED,",
        "  third_party_reported THIRD_PARTY_REPORTED, inferred INFERRED, not_found UNRESOLVED.",
        "- Severity (worst first): CONFLICTING, UNRESOLVED, INFERRED, THIRD_PARTY_REPORTED, SELF_REPORTED,",
        "  CONFIRMED.",
        "",
        "### Counting rule (derived, never stored)",
        "",
        "- Allocation rows cover interfaces of kind L1_L2, sleeve_holding, reserve_lookthrough and asset_sale.",
        "- An amount is counted only when the kind is L1_L2 or sleeve_holding, amount_basis is GROSS_FUNDED, the",
        "  amount has a value and alternative.group is null. Totals are summed per strategy and per component,",
        "  grouped by currency value (`n/d` when the currency is null); everything else is linked, not summed.",
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
