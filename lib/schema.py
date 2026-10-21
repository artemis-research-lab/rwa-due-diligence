"""Schema rwa-dd/2.2: the single definition of the DD document, its enums and field limits.

references/schema.md is generated from this module (`dd.py schema-doc`).
"""

SCHEMA_VERSION = "rwa-dd/2.2"
SKILL_VERSION = "0.7.2"

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
    "amount_basis": ("CURRENT_BALANCE", "POSITION_VALUE", "OUTSTANDING_PRINCIPAL", "CUMULATIVE_FUNDED",
                     "FACILITY_COMMITMENT", "UNDRAWN_COMMITMENT", "SALE_PROCEEDS", "RESERVE_LOOKTHROUGH", "OTHER"),
    "assertion_origin": ("issuer_management", "issuer_documents", "borrower", "regulator", "registry", "onchain",
                         "independent_party", "auditor_procedure", "analyst"),
    "assurance_scope": ("TESTED", "NOT_TESTED", "NOT_APPLICABLE"),
    "deployment": ("DEPLOYED_VERIFIED", "DISCLOSED_UNVERIFIED", "NOT_DEPLOYED", "UNRESOLVED"),
    "scope_match": ("matched", "not_matched", "unchecked", "not_applicable"),
    "resolution_status": ("open", "resolved", "not_applicable"),
    "k_check": ("K1", "K2", "K3", "K4", "K5", "K6", "K7"),
    "impact": ("credit_exposure", "investor_rights", "governance", "capital_control", "ownership", "redemption",
               "enforcement", "security", "recovery", "liquidity"),
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
    "finding_type": ("gap", "discrepancy", "structural_change", "scope_unresolved", "unreconciled_transaction"),
    "topic": ("legal", "yield", "flows", "onchain", "redemption", "credit", "holder_rights", "business", "other"),
    "size_metric": ("tvl", "supply", "nav", "holders", "reserves", "originated", "outstanding", "defaulted"),
    "run_status": ("draft", "final"),
    "claim_status": ("verified", "self_reported", "third_party_reported", "inferred", "not_found"),
}

# Finding id prefix per finding type.
FINDING_PREFIX = {"gap": "G", "discrepancy": "D", "structural_change": "C", "scope_unresolved": "U",
                  "unreconciled_transaction": "R"}

# Assertion origins that are issuer statements wherever they are published (curator Q8).
ISSUER_ORIGINS = ("issuer_management", "issuer_documents", "borrower")
# Impacts that place a blocking finding in report section 1 (curator Q10).
SECTION1_IMPACTS = ("capital_control", "ownership", "redemption", "enforcement", "security")

# Limits that are not part of a single field.
CLAIM_NOTE_MAX = 200
CLAIM_VALUE_STR_MAX = 300
SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{1,40}$"

# Top-level sections whose claims are legal facts (claim rules, section 3.3).
LEGAL_SECTIONS = ("entities", "interfaces", "holder_rights", "supports", "eligibility")

# Scope note of a discrepancy carried over from rwa-dd/2.0 (migration, review packet, finalize).
MIGRATED_SCOPE_NOTE = "unchecked (migrated from rwa-dd/2.0)"
# Scope note of a discrepancy or scope_unresolved finding carried over from rwa-dd/2.1.
MIGRATED_NOTE_21 = "unchecked (migrated from rwa-dd/2.1)"
# Scope of an amount converted from a rwa-dd/2.1 interface amount.
MIGRATED_AMOUNT_SCOPE = "unchecked (migrated from rwa-dd/2.1)"
MIGRATION_PLACEHOLDERS = (MIGRATED_SCOPE_NOTE, MIGRATED_NOTE_21)

# Coded claims (D39): (section, field) -> (enum, shape); shape "one" = one enum string, "list" = non-empty list
# of enum strings without duplicates, "strings" = non-empty ordered list of strings, "number" = an int or float
# >= 0 that is not a boolean, "ratio" = an int or float 0..1 that is not a boolean.
CODED_CLAIMS = {
    ("strategies", "business_type"): ("business_type", "one"),
    ("interfaces", "route"): ("route_code", "one"),
    ("interfaces", "method"): ("method_code", "list"),
    ("interfaces", "legal_class"): ("legal_class", "one"),
    ("interfaces", "security"): ("security", "one"),
    ("holder_rights", "look_through"): ("look_through", "one"),
    ("strategies", "loss_waterfall"): (None, "strings"),
    ("interfaces", "value"): (None, "number"),
    ("interfaces", "ratio"): (None, "ratio"),
    ("strategies", "deployment"): ("deployment", "one"),
}

SUBJECT_PATTERN = r"^(E|P|T|X|Z)[1-9][0-9]*(\.[a-z][a-z0-9_]*(\[[0-9]+\])?){0,4}$"


def id_pattern(*prefixes):
    return r"^(%s)[1-9][0-9]*$" % "|".join(prefixes)


def is_placeholder(note):
    """True when a scope note starts with a migration placeholder text."""
    return isinstance(note, str) and note.startswith(MIGRATION_PLACEHOLDERS)


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
    def __init__(self, minimum, maximum=None, nullable=False):
        self.minimum = minimum
        self.maximum = maximum
        self.nullable = nullable

    def describe(self):
        if self.maximum is not None:
            text = "integer %d..%d" % (self.minimum, self.maximum)
        else:
            text = "integer >=%d" % self.minimum
        return text + (" | null" if self.nullable else "")


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


def DateOrTimestamp(nullable=False):
    return Pattern(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)?$",
                   "date YYYY-MM-DD or timestamp YYYY-MM-DDTHH:MM:SSZ", nullable=nullable,
                   kind="date_or_timestamp")


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
    ("deployment", C),
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

AMOUNT = Obj(
    ("basis", Enum("amount_basis")),
    ("value", C),
    ("unit", Str(20)),
    ("as_of", DateOrTimestamp(nullable=True)),
    ("block", Int(0, nullable=True)),
    ("chain", Str(24, nullable=True)),
    ("scope", Str(200)),
    ("valuation_basis", Str(120, nullable=True)),
)

SUPPLY_CONCENTRATION = Obj(
    ("ratio", C),
    ("numerator", Str(160)),
    ("denominator", Str(160)),
    ("as_of", DateOrTimestamp(nullable=True)),
    ("block", Int(0, nullable=True)),
    ("chain", Str(24, nullable=True)),
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
    ("amounts", Arr(AMOUNT)),
    ("supply_concentration", SUPPLY_CONCENTRATION),
    ("title_transfer", C),
    ("servicing", C),
    ("residual_exposure", C),
    ("loan_identity", C),
    ("seller_of_record", C),
    ("buyer_of_record", C),
    ("repayment_source", C),
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
        ("id", Ref("G", "D", "C", "U", "R")),
        ("type", Enum("finding_type")),
        ("topic", Enum("topic")),
        ("blocking", Bool()),
        ("material", Bool()),
        ("statement", Str(280)),
        ("scope_note", Str(200)),
        ("scope_match", Enum("scope_match")),
        ("evidence", Arr(Ref("S"))),
        ("subjects", Arr(Pattern(SUBJECT_PATTERN, "subject path (E|P|T|X|Z)<n>[.field[<i>]]{0,4}"))),
        ("assertions", Arr(Obj(
            ("source", Ref("S")),
            ("statement", Str(200)),
            ("as_of", Date()),
        ))),
        ("resolution", Obj(
            ("status", Enum("resolution_status")),
            ("note", Str(200)),
        )),
        ("k_checks", Arr(Enum("k_check"))),
        ("impact", Arr(Enum("impact"))),
        ("priority", Int(1, 3)),
        ("carried_from", Pattern(r"^[GDCUR][1-9][0-9]*$", "finding id G|D|C|U|R<n>", nullable=True)),
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
        ("resolves", Arr(Ref("G", "D", "U", "R"))),
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

CLAIM_KEYS = ("value", "status", "evidence", "subject", "note", "origin", "assurance")


# --------------------------------------------------------------------------- helpers

def empty_claim():
    return {"value": None, "status": "not_found", "evidence": [], "subject": None, "note": "", "origin": None,
            "assurance": None}


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
    if node.nullable:
        return None
    if isinstance(node, Int):
        return node.minimum
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


# Curator meanings of the amount bases (v0.7.0 9.1); legend and schema doc.
AMOUNT_BASIS_MEANINGS = (
    ("CURRENT_BALANCE", "token or asset holdings at the data time"),
    ("POSITION_VALUE", "value of a position under a stated valuation basis"),
    ("OUTSTANDING_PRINCIPAL", "loan principal unpaid at the data time (recorded unbilled principal goes"
                              " here with the scope saying so)"),
    ("CUMULATIVE_FUNDED", "actual disbursements over a stated period"),
    ("FACILITY_COMMITMENT", "contractual ceiling"),
    ("UNDRAWN_COMMITMENT", "unused part of a facility commitment"),
    ("SALE_PROCEEDS", "proceeds actually received from a disposal"),
    ("RESERVE_LOOKTHROUGH", "an issuer's reserve or collateral assets, never additive"),
    ("OTHER", "only with a scope of at least 20 characters defining it"),
)

# Bases summed into totals (v0.7.0 3.4).
COUNTABLE = ("CURRENT_BALANCE", "POSITION_VALUE", "OUTSTANDING_PRINCIPAL")

# Quantitative and provenance checks (v0.7.0 6.1): (id, rule name, text).
QA_RULES = (
    ("QA1", "basis", "No total mixes amount bases, units, valuation bases or data dates (each total"
                     " recomputed from the allocation rows has one total key and the same sum)."),
    ("QA2", "lookthrough", "No RESERVE_LOOKTHROUGH amount and no reserve_lookthrough interface is counted."),
    ("QA3", "alternative", "No amount on an interface with an alternative group is counted."),
    ("QA4", "proceeds", "No SALE_PROCEEDS amount is counted; SALE_PROCEEDS amounts whose value status is not"
                        " verified are listed as unverified (informational)."),
    ("QA5", "asof", "No amount with as_of null is counted."),
    ("QA6", "stockflow", "No CUMULATIVE_FUNDED, FACILITY_COMMITMENT or UNDRAWN_COMMITMENT amount is counted or"
                         " labelled outstanding in totals."),
    ("QA7", "provenance", "No claim citing an auditor source (outside audits[]) has origin null; no claim with an"
                          " issuer origin has status other than self_reported or not_found; every origin, assurance"
                          " and status combination follows the curator Q8 rules."),
    ("QA8", "conflicts", "Every claim flagged CONFLICTING is a subject of an open discrepancy with scope_match"
                         " matched and at least two assertions; no scope_unresolved or unreconciled_transaction"
                         " subject is flagged CONFLICTING."),
    ("QA9", "placeholder", "No finding scope note and no amount scope is a migration placeholder."),
    ("QA10", "section1", "Every material finding and every blocking finding with k_checks is in section 1."),
    ("QA11", "deployment", "No CORE_CREDIT or DEFI_LENDING strategy has deployment DEPLOYED_VERIFIED without"
                           " status verified."),
    ("QA12", "onemeasure", "No interface has more than one counted amount (entry 0 or the first countable entry is"
                           " the position measure; later entries are other measures of the same position)."),
    ("QA13", "timebasis", "No counted amount lacks an established data time, and no data time is a source retrieval"
                          " time (curator AC-03)."),
)

# Expectation operators (v0.7.0 6.2).
EXPECT_OPS = ("equals", "in", "status", "flag", "counted", "exists", "not_contains")


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
        "  X (interfaces), Z (supports), n (flow nodes), G/D/C/U/R (findings, each prefix counted separately),",
        "  N (next searches), Q (issuer requests).",
        "- Finding id prefix follows the type: gap=G, discrepancy=D, structural_change=C, scope_unresolved=U,",
        "  unreconciled_transaction=R.",
        "- Migration placeholders: a finding scope note that starts with `%s` or" % MIGRATED_SCOPE_NOTE,
        "  `%s`, and an amount scope equal to `%s`;" % (MIGRATED_NOTE_21, MIGRATED_AMOUNT_SCOPE),
        "  finalize refuses them.",
        "- Every product is in at least one strategy, has exactly one holder_rights entry and at least one yield",
        "  entry. Every strategy with component CORE_CREDIT or DEFI_LENDING has at least one flow edge with view",
        "  settlement (LIQUIDITY_SLEEVE is exempt).",
        "- Interface `from` is a product id (its token holders) exactly when kind is holder_L1; otherwise an entity;",
        "  `from` and `to` differ.",
        "- `entities[].functions[].layer` may be null only for the roles issuer, loan_purchaser,",
        "  protection_provider, reserve_assets, auditor and other.",
        "- `interfaces[].alternative`: `group` and `option` are both null or both set; a group has at least two",
        "  distinct options and all its interfaces belong to one strategy.",
        "- `interfaces[].as_of` is the date the legal terms were observed; an amount's `as_of` is its data time",
        "  (see Amounts); source retrieval times are `sources[].retrieved_at`; the report generation time is",
        "  `run.finalized_at` (never merged with any of them).",
        "- `supports[]`: `strategies` are T ids, `provider` an E id, `beneficiary` an E or P id or null.",
        "- `findings[].subjects` name claims or objects by claim id (see Evidence flags); the path must resolve.",
        "- `history` is sorted by date, nulls last.",
        "- `sources` must equal the source ledger `audit/sources.jsonl`; add sources only with `dd.py add-source`.",
        "- A date-or-timestamp is a real calendar date `YYYY-MM-DD`, optionally with a valid time",
        "  `THH:MM:SSZ`.",
        "",
        "## Claim",
        "",
        "- `value`: any JSON or null; each string inside it <=%d" % CLAIM_VALUE_STR_MAX,
        "- `status`: enum claim_status",
        "- `evidence`: array of id S<n> (the publication sources)",
        "- `subject`: id E<n>|P<n> | null",
        "- `note`: string <=%d (may be empty)" % CLAIM_NOTE_MAX,
        "- `origin`: enum assertion_origin | null: who originally asserted the fact; null means the publisher of",
        "  the cited evidence is the asserter.",
        "- `assurance`: enum assurance_scope | null: what an auditor or independent reviewer tested for this",
        "  precise claim; null means no auditor or reviewer procedure is cited.",
        "",
        "### Claim rules",
        "",
        "Evidence role of source s for claim c: `self` if s.origin is first_party or s.publisher equals",
        "c.subject; `analyst` if s.origin is analyst; otherwise `independent:<origin>`.",
        "Legal paths: %s. Issuer origins: %s." % (", ".join(LEGAL_SECTIONS), ", ".join(ISSUER_ORIGINS)),
        "",
        "- verified: at least one independent evidence and no analyst evidence; on legal paths its origin must be",
        "  regulator, registry, auditor or onchain. When any cited source has origin auditor: origin",
        "  auditor_procedure with assurance TESTED, or origin regulator, registry or onchain with a source of that",
        "  same origin in evidence and assurance TESTED or NOT_TESTED; any other origin is an error. An auditor",
        "  source counts for the legal rule only with origin auditor_procedure and assurance TESTED.",
        "- The auditor-source rules (curator Q8) apply once origin is set; a null origin is unstated: valid, but",
        "  lint warns, QA7 fails and finalize refuses. Claims under audits[] describe the audit itself and are",
        "  exempt from them.",
        "- self_reported: at least one self evidence, or an issuer origin with non-empty evidence (an issuer",
        "  statement quoted in an auditor or third-party publication).",
        "- third_party_reported: at least one independent evidence of any origin (allowed on legal paths; it is",
        "  not verification). Citing only auditor sources requires origin independent_party or auditor_procedure.",
        "- inferred: at least one evidence and a non-empty note; origin analyst or null.",
        "- verified, self_reported, third_party_reported and inferred: value is not null.",
        "- not_found: value is null, origin and assurance are null; if evidence is non-empty the note must be",
        "  non-empty.",
        "- An issuer origin allows only self_reported or not_found (curator Q8). Origin auditor_procedure needs an",
        "  auditor source and assurance TESTED or NOT_TESTED; with TESTED the status must be verified, with",
        "  NOT_TESTED third_party_reported. Origin analyst allows only inferred or not_found, and no assurance.",
        "- assurance non-null needs an auditor source in evidence (under audits[]: an auditor or other",
        "  independent source).",
        "- subject references an existing entity or product, or is null.",
        "",
        "### Coded claims",
        "",
        "When the value is not null:",
        "",
        "- `strategies[].business_type`, `strategies[].deployment`, `interfaces[].route`, `interfaces[].legal_class`,",
        "  `interfaces[].security` and `holder_rights[].look_through`: one string from enum business_type,",
        "  deployment, route_code, legal_class, security and look_through respectively.",
        "- `interfaces[].method`: a non-empty list of method_code strings without duplicates.",
        "- `strategies[].default_path.loss_waterfall`: a non-empty ordered list of strings (the first absorbs",
        "  losses first).",
        "- `interfaces[].amounts[].value`: a number >= 0 (an integer or a float, not a boolean).",
        "- `interfaces[].supply_concentration.ratio`: a number 0..1 (an integer or a float, not a boolean).",
        "",
        "Kind constraints: these interface fields must be not_found with empty evidence (or empty) unless the kind",
        "matches: `route` and `supply_concentration` (L1_L2); `method` (L2_L3 or L3_L3O); `title_transfer`,",
        "`servicing`, `residual_exposure`, `loan_identity`, `seller_of_record`, `buyer_of_record` and",
        "`repayment_source` (asset_sale). `deployment` is set only on CORE_CREDIT and DEFI_LENDING strategies;",
        "DEPLOYED_VERIFIED requires status verified.",
        "",
        "### Amounts",
        "",
        "Each `interfaces[].amounts[]` entry is one measured number: `basis`, `value` (a claim that is not",
        "not_found), `unit` (token symbol or currency, non-empty), `as_of` (data time, see below), `block` and",
        "`chain` (chain required when block is set), `scope` (what is measured, non-empty) and `valuation_basis`",
        "(required for POSITION_VALUE).",
        "",
        "Time basis (curator AC-03):",
        "",
        "- `as_of` is data_as_of: the date or time the value applies, as established by the source (a statement",
        "  or report date, an API `updatedAt`, or the block time of an on-chain read); null when the source does",
        "  not establish it. It is never the time a page was opened or the report date.",
        "- block_timestamp: when `block` is set, `as_of` is that block's time and must be a full timestamp.",
        "- Without a block, `as_of` never equals (same string, or same instant when both are timestamps) the",
        "  `retrieved_at` of a source cited in the value's evidence.",
        "- observed_at (derived, never stored): the latest `retrieved_at` among the sources cited in the value's",
        "  evidence; null when none has one.",
        "- time basis (derived): `block` (block set), `source` (as_of set, no block), `unresolved` (as_of null).",
        "",
        "Bases:",
        "",
    ]
    lines += ["- `%s`: %s." % (name, meaning) for name, meaning in AMOUNT_BASIS_MEANINGS]
    lines += [
        "",
        "Amounts are allowed on L1_L2, L2_L3, within_L1, within_L2, sleeve_holding, reserve_lookthrough and",
        "asset_sale interfaces. RESERVE_LOOKTHROUGH only on reserve_lookthrough; SALE_PROCEEDS only on asset_sale;",
        "FACILITY_COMMITMENT and UNDRAWN_COMMITMENT only on L1_L2, L2_L3 and within_L2.",
        "`supply_concentration` (L1_L2 only) is pool supply concentration: `ratio` (a claim), `numerator`,",
        "`denominator`, `as_of`, `block`, `chain`; numerator, denominator and as_of are required with a ratio.",
        "",
        "### Findings",
        "",
        "- `scope_match`: gap and structural_change not_applicable; discrepancy matched (unchecked only while the",
        "  scope note is a migration placeholder); scope_unresolved not_matched or unchecked;",
        "  unreconciled_transaction any value except not_applicable.",
        "- discrepancy, scope_unresolved and unreconciled_transaction need a scope note and, unless it is a",
        "  migration placeholder, at least two `assertions` (source, statement, as_of); each assertion source is in",
        "  the finding's evidence. gap and structural_change have no assertions.",
        "- A discrepancy names at least one subject (unless its scope note is a migration placeholder) and every",
        "  subject resolves to a claim; other subjects resolve to an object or a claim.",
        "- `resolution.status`: open or resolved (resolved needs a note); structural_change not_applicable.",
        "- `k_checks` (K1-K7) and `impact` without duplicates; `priority` 1-3 (1 decides the credit picture);",
        "  `carried_from` is the id the finding had in the run this one was seeded from, unique across findings.",
        "",
        "### Evidence flags and conflict statuses (derived, never stored)",
        "",
        "- Claim id: the id of the nearest enclosing object that has an `id` in E, P, T, X or Z, followed by the",
        "  field path below it with `[n]` for array positions (for example `X3.security`,",
        "  `X2.amounts[0].value`, `X4.supply_concentration.ratio`, `T1.default_path.loss_waterfall`,",
        "  `Z1.coverage`). Holder-rights claims take their product's id: `P<n>.holder_rights.<field>`. Claims",
        "  outside such objects use the document path (`project.name`, `yield[0].gross_yield`).",
        "- A claim is CONFLICTING only when it is a subject (or below a subject at a field boundary) of a",
        "  discrepancy with scope_match matched and resolution open. scope_unresolved and",
        "  unreconciled_transaction findings and resolved discrepancies never flag a claim.",
        "- Six flags: CONFLICTING if conflicting; otherwise verified gives CONFIRMED, self_reported SELF_REPORTED,",
        "  third_party_reported THIRD_PARTY_REPORTED, inferred INFERRED, not_found UNRESOLVED.",
        "- Severity (worst first): CONFLICTING, UNRESOLVED, INFERRED, THIRD_PARTY_REPORTED, SELF_REPORTED,",
        "  CONFIRMED.",
        "- Conflict status of a finding: CONFLICTING (open matched discrepancy), RESOLVED (resolved discrepancy),",
        "  SCOPE_UNRESOLVED (scope_unresolved), UNRECONCILED_TRANSACTION (unreconciled_transaction); none for",
        "  gaps and structural changes.",
        "",
        "### Counting rule (derived, never stored)",
        "",
        "- Allocation rows: one per amount entry on interfaces of kind L1_L2, sleeve_holding, reserve_lookthrough",
        "  and asset_sale; such an interface without amounts gives one row with reason `no amount`.",
        "- Counted only when the kind is L1_L2 or sleeve_holding, the basis is %s, the value" % ", ".join(COUNTABLE),
        "  is set, as_of (the data time) is set, alternative.group is null and the scope is not the migration",
        "  placeholder.",
        "- One edge is one position: only the first entry (lowest index) of an interface that meets these",
        "  conditions is counted; each later one gets reason `other measure of X<n>[<k>]` (k the counted entry).",
        "- Reasons (first that applies): `alternative A<n><o>`, `not a funding edge`, `basis <BASIS> not counted`,",
        "  `no amount`, `data time not established`, `migrated scope`, `other measure of X<n>[<k>]`, `counted`.",
        "- Totals per strategy, component and product add only counted amounts with the same total key (basis,",
        "  unit, data date YYYY-MM-DD, valuation basis); two keys are never added. Label:",
        "  `<sum> <unit> <BASIS> @<date>`.",
        "",
        "## Quality checks (dd.py qa)",
        "",
    ]
    lines += ["- %s %s: %s" % rule for rule in QA_RULES]
    lines += [
        "",
        "Expectations (`--expect <file>`, default `audit/qa-expect.json` when it exists; written by the analyst and",
        'never edited by the agent): a JSON array of `{"id": <1..20 chars>, "case": <<=120 chars>, "path": <path>,',
        '"op": <op>, "value": <json>}`, optionally with `"target": <id>` (`(E|P|T|X|Z|G|D|C|U|R)<n>`, the',
        "canonical id the path must resolve to). Paths: `(@?)(E|P|T|X|Z|G|D|C|U|R)<n>` followed by `.field` and",
        "`[i]` parts; `@<id>` selects the finding carried from that id and needs `target` (curator AC-01).",
        "Ops: %s." % ", ".join(EXPECT_OPS),
        "Each gives a result `E:<id>` after QA13. Every result has `id`, `rule`, `result`, `detail`, `target`",
        "(canonical id, null when unresolved or for QA rules), `legacy` (the `@` id or null) and `mapping` (legacy",
        "or carried_from mapping text, empty when none); an expectation detail starts with `<canonical id>: `, and",
        "a `target` that differs from the resolved id fails with `target mismatch: expected <a>, resolved <b>`.",
        "`dd.py qa` exits 5 when any check fails.",
        "",
        "## Derived output",
        "",
        "Finalize writes `<slug>.derived.json` (`derived_version` `rwa-dd-derived/1`) next to `<slug>.dd.json`:",
        "slug, run_id, schema_version, skill_version, `record_sha256` (SHA-256 of the written dd.json bytes),",
        "`flags` (claim id -> flag for every claim), `conflicts`, `critical`, `critical_counts`, `allocation`,",
        "`totals`, `five_questions`, `qa` and `changes`. Flags and totals are derived, never stored in the record.",
        "Allocation rows carry `observed_at` and `time_basis`.",
        "",
        "## Package manifest",
        "",
        "Finalize then writes `<slug>.manifest.json` (`manifest_version` `rwa-dd-manifest/1`): slug, run_id,",
        "seeded_from, schema_version, skill_version, finalized_at, rounds, `execution` (python, platform, d2),",
        "`files` (path relative to the project directory, role, bytes, sha256; sorted by path; roles record,",
        "derived, report, diagram, ledger, expectations, run_state, round_record, analyst_input; never itself) and",
        "`checks` (validate_errors, lint_warnings, qa_failed, record_sha256_match). `dd.py verify` recomputes them",
        "read-only and exits 6 when the package does not reproduce.",
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
