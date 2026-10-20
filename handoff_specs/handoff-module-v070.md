# handoff-module-v070 -- rwa-due-diligence v0.7.0: measurement, provenance, conflicts (schema rwa-dd/2.2)

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. build the module in handoff_specs/handoff-module-v070.md"

## 0. Persistent context
- Read `docs/architecture.md` before executing; this spec replaces it (9.4).
- Base: `main` = `4c87ded3a18ef4e49f5a7a3ce1032b1bc50d0c03` (v0.6.0 plus spec commit). Target: **SKILL_VERSION 0.7.0**,
  **SCHEMA rwa-dd/2.2**.
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v070-measurement` from main, one commit, push it. Do not touch `main`. Do not commit anything under
  `handoff_specs/`.
- D1-D63 apply unless replaced below; this module adds D64-D76 (section 10).
- Scripts stay OS-neutral Python, standard library only (pypdf and d2 as before). No network code outside lib/fetch.py.
- No HTML output in this module (HTML readers are deferred until the data model is accepted).

### 0.1 Why
The risk curator reviewed the v2.1 samples (2026-10-20) and asked for a minor data-model revision (documents: Answers
Q8-Q10, Remaining Sample Issues, Cross-Project Data Corrections and v2.2 Acceptance). Requirements:
- P0 Amount basis: typed measurement bases (CURRENT_BALANCE, POSITION_VALUE, OUTSTANDING_PRINCIPAL, CUMULATIVE_FUNDED,
  FACILITY_COMMITMENT, UNDRAWN_COMMITMENT, SALE_PROCEEDS, RESERVE_LOOKTHROUGH, OTHER); GROSS_FUNDED retired; every
  amount carries unit, observation time, block and chain where applicable, measurement scope, valuation basis and
  source; incompatible concepts never summed.
- P0 Provenance (Q8): a management statement quoted in an AUP stays SELF_REPORTED; the auditor is the publication
  source; assurance scope NOT_TESTED for that claim. Origin, verification, publication and assurance are separate.
- P0 Conflicts: claim-level CONFLICTING is traceable in JSON; same-scope conflicts are distinguished from
  scope-unresolved items and unreconciled transactions; scope match and resolution status are explicit.
- P1 Timestamps: each value keeps its observation time; report generation time is separate.
- P1 Deployment: a disclosed but unverified deployment (Huma PST -> Arf) is never shown as confirmed deployed credit.
- P1 Asset-sale reconciliation (USD.AI U9): loan identity, seller and buyer of record, legal transfer method,
  repayment source, servicer after exit and retained exposure tracked separately; no unsupported conclusion.
- P1 Section 1 (Q10): material findings, blocking gaps on K1-K7 and other significant control/ownership/redemption/
  enforcement/security issues; target 5-8 entries with counts and a pointer to section 6; nothing dropped.
- P2 Automated quantitative-semantic QA, with assertion results delivered with each sample, plus a change log against
  the previous run.
Backlog folded in: research-protocol section 3 table, directives and next_searches accept U and R ids, run-scoped log
file names, digit-only fake addresses in new tests.

### 0.2 Verified shared contracts (base commit)
```
lib/schema.py: SCHEMA_VERSION "rwa-dd/2.1", SKILL_VERSION "0.6.0"; ENUMS amount_basis GROSS_FUNDED|COMMITMENT|
  LOOKTHROUGH|RESERVE|SALE_PROCEEDS; finding_type gap|discrepancy|structural_change|scope_unresolved;
  FINDING_PREFIX G/D/C/U; MIGRATED_SCOPE_NOTE "unchecked (migrated from rwa-dd/2.0)"; CODED_CLAIMS keyed
  (parts[0], parts[-1]) incl. ("interfaces","amount") -> (None,"number"); SUBJECT_PATTERN
  ^(E|P|T|X|Z)[1-9][0-9]*(\.[a-z][a-z0-9_]*){0,3}$; INTERFACE has amount C, amount_basis Enum nullable,
  supply_concentration C, title_transfer C, servicing C, residual_exposure C, as_of Date; findings id Ref G|D|C|U,
  material Bool, scope_note Str(200); next_searches.resolves Arr(Ref G|D); CLAIM_KEYS value,status,evidence,subject,note;
  Int(minimum, maximum) has no nullable
lib/claims.py: LEGAL_VERIFIERS regulator|registry|auditor|onchain; evidence_role(source, claim) -> self|analyst|
  independent:<origin>; check_claim(parts, claim, sources_by_id, subject_ids)
lib/validate.py: coded lookup schema.CODED_CLAIMS.get((parts[0], parts[-1])); finding id density per prefix G,D,C,U
lib/framework.py: subject_path, conflicted, flag, flags, SEVERITY, worst, CHECKS K1-K7, core_strategies,
  completeness, chain_line, allocation, allocation_totals, five_questions
lib/migrate.py: convert (1.0->2.0), convert_20 (2.0->2.1), migrate_to_current
lib/runstate.py: _seed_version accepts 1.0, 2.0, 2.1; seed archives the old run to archive/<run_id>/ (its final
  <slug>.dd.json and audit/ move there); finalize refuses MIGRATED_SCOPE_NOTE on discrepancies, sets skill_version
lib/lint.py: lint(doc) -> address_warnings, layer_warnings, claim_warnings, path_warnings
lib/directives.py: _GD = r"[GD][1-9][0-9]*" (answer, drop)
lib/render_md.py: six reader sections + Appendices A-M
tests/fixtures: acme.dd.json (2.1), acme_v2.dd.json (2.0), acme_v1.dd.json (1.0), acme.sources.jsonl, sample.pdf
tests/golden: acme.report.md, acme.review.md, acme_v1.migrated.json, acme_v2.migrated.json, flow d2/svg goldens
```
If any of these differs at the base commit, STOP and report.

### 0.3 File scope (HARD)
```
[EDIT] lib/schema.py, lib/claims.py, lib/validate.py, lib/framework.py, lib/migrate.py, lib/lint.py, lib/runstate.py,
       lib/review.py, lib/render_md.py, lib/flow.py (only if a test needs it), lib/directives.py (id pattern only),
       lib/textutil.py (helpers only), scripts/dd.py
[NEW]  lib/qa.py, lib/changes.py
[EDIT] references/schema.md (regenerated), references/research-protocol.md (VERBATIM 9.1), SKILL.md (VERBATIM 9.2),
       docs/architecture.md (VERBATIM 9.4, whole file), docs/decisions.md (section 10)
[EDIT/NEW] tests/fixtures/acme.dd.json (2.2), tests/fixtures/acme_v21.dd.json (git mv of the current 2.1 fixture),
       tests/fixtures/acme.qa-expect.json (NEW), tests/golden/* (regenerated; list every file),
       tests/golden/acme_v21.migrated.json (NEW), tests/unit/* as needed (new: test_qa.py, test_changes.py)
[REUSE -- DO NOT TOUCH] lib/fetch.py, lib/pdftext.py, lib/ledger.py, assets/**, tools/**, references/runtime.md,
  references/third-party.md, references/source-registry.md, CLAUDE.md, .gitattributes, pytest.ini, .gitignore,
  handoff_specs/** (except the results file in section 12)
```

### 0.4 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-module-v070.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` =
`4c87ded3a18ef4e49f5a7a3ce1032b1bc50d0c03`; `git status --porcelain` shows only untracked entries under
`handoff_specs/`; `python --version` >= 3.11; `d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. Schema rwa-dd/2.2 (lib/schema.py)

`SCHEMA_VERSION = "rwa-dd/2.2"`, `SKILL_VERSION = "0.7.0"`. Everything not listed stays as in 2.1.

### 1.1 Enums
```
amount_basis = CURRENT_BALANCE, POSITION_VALUE, OUTSTANDING_PRINCIPAL, CUMULATIVE_FUNDED, FACILITY_COMMITMENT,
               UNDRAWN_COMMITMENT, SALE_PROCEEDS, RESERVE_LOOKTHROUGH, OTHER          (replaces the 2.1 list)
assertion_origin = issuer_management, issuer_documents, borrower, regulator, registry, onchain, independent_party,
                   auditor_procedure, analyst
assurance_scope = TESTED, NOT_TESTED, NOT_APPLICABLE
deployment = DEPLOYED_VERIFIED, DISCLOSED_UNVERIFIED, NOT_DEPLOYED, UNRESOLVED
finding_type += unreconciled_transaction          (FINDING_PREFIX R)
scope_match = matched, not_matched, unchecked, not_applicable
resolution_status = open, resolved, not_applicable
k_check = K1, K2, K3, K4, K5, K6, K7
impact = credit_exposure, investor_rights, governance, capital_control, ownership, redemption, enforcement, security,
         recovery, liquidity
```
`ISSUER_ORIGINS = ("issuer_management", "issuer_documents", "borrower")`.
`SECTION1_IMPACTS = ("capital_control", "ownership", "redemption", "enforcement", "security")`.

### 1.2 Claim shape
`CLAIM_KEYS = ("value", "status", "evidence", "subject", "note", "origin", "assurance")`.
- `origin`: Enum assertion_origin, nullable. Who originally asserted the fact. Null means the publisher of the cited
  evidence is the asserter (the 2.1 meaning). The cited evidence sources are the publication sources.
- `assurance`: Enum assurance_scope, nullable. What an auditor or independent reviewer actually tested for this
  precise claim. Null means no auditor or reviewer procedure is cited.
`empty_claim()` (and every skeleton/migration helper) emits both keys as null. Key order as above.

### 1.3 Document changes
```
strategies[]: + deployment: C (coded one-of deployment)                      (after business_type)
interfaces[]: - amount, - amount_basis
              + amounts: Arr(AMOUNT)                                          (where amount was)
              supply_concentration: C  ->  Obj(
                  ratio: C (coded "ratio": a number 0..1, not a bool),
                  numerator: Str(160), denominator: Str(160),
                  as_of: DateOrTimestamp nullable, block: Int(0, nullable), chain: Str(24, nullable))
              + loan_identity: C, seller_of_record: C, buyer_of_record: C, repayment_source: C
                                                                              (after residual_exposure)
              as_of: Date (unchanged; meaning narrowed to the date the legal terms were observed, see 9.1)
AMOUNT = Obj(
  basis: Enum amount_basis
  value: C (coded "number")
  unit: Str(20)                         (token symbol or currency, e.g. YLDS, USDC, USD; required, non-empty)
  as_of: DateOrTimestamp nullable       (observation time of the value; never the report date)
  block: Int(0, nullable)
  chain: Str(24, nullable)
  scope: Str(200)                       (what is measured: population, period, account; required, non-empty)
  valuation_basis: Str(120, nullable))  (required for POSITION_VALUE)
findings[]: id Ref G|D|C|U|R
            + scope_match: Enum scope_match                                   (after scope_note)
            + assertions: Arr(Obj(source: Ref S, statement: Str(200), as_of: Date nullable))
            + resolution: Obj(status: Enum resolution_status, note: Str(200))
            + k_checks: Arr(Enum k_check)
            + impact: Arr(Enum impact)
            + priority: Int(1, 3)
            + carried_from: Pattern ^[GDCUR][1-9][0-9]*$ nullable
            subjects: Arr(Pattern SUBJECT_PATTERN)
next_searches[].resolves: Arr(Ref G|D|U|R)
```
New node helpers: `Int(minimum, maximum=None, nullable=False)` (describe appends ` | null`), and
`DateOrTimestamp(nullable)` = Pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}(T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)?$`, label
`date YYYY-MM-DD or timestamp YYYY-MM-DDTHH:MM:SSZ`, kind `date_or_timestamp` (semantic check: a real calendar date
and, when present, a valid time).
`SUBJECT_PATTERN = ^(E|P|T|X|Z)[1-9][0-9]*(\.[a-z][a-z0-9_]*(\[[0-9]+\])?){0,4}$` (so `X2.amounts[0].value` and
`X4.supply_concentration.ratio` are subjects).
`CODED_CLAIMS`: remove ("interfaces","amount"); add ("interfaces","value") -> (None,"number"),
("interfaces","ratio") -> (None,"ratio"), ("strategies","deployment") -> ("deployment","one"). Shape "ratio": int or
float, 0 <= x <= 1, not a bool.
Constants: `MIGRATED_SCOPE_NOTE` stays (2.0); add `MIGRATED_NOTE_21 = "unchecked (migrated from rwa-dd/2.1)"` and
`MIGRATED_AMOUNT_SCOPE = "unchecked (migrated from rwa-dd/2.1)"`; `MIGRATION_PLACEHOLDERS = (MIGRATED_SCOPE_NOTE,
MIGRATED_NOTE_21)`.
`schema_doc()` documents every addition: the nine bases with the curator's meanings (9.1 text), the claim keys origin
and assurance, the finding fields, conflict statuses (3.1), the counting rule (3.4), the QA rules (6), the
expectation-file format (6.2) and the derived output (7.3). Regenerate references/schema.md.

## 2. Claims and validation

### 2.1 lib/claims.py (curator Q8)
Existing status rules stay, with these changes and additions (error texts exact):
- self_reported: passes when a "self" role is present (as now) OR `origin` is in ISSUER_ORIGINS and evidence is
  non-empty (an issuer statement quoted in an auditor or third-party publication).
- `origin` in ISSUER_ORIGINS and status not in (self_reported, not_found):
  `<path>: origin <origin> is an issuer assertion; status must be self_reported (curator Q8)`.
- `origin == auditor_procedure`: evidence must include a source with origin auditor
  (`<path>: origin auditor_procedure requires an auditor source`) and `assurance` must be TESTED or NOT_TESTED
  (`<path>: origin auditor_procedure requires assurance TESTED or NOT_TESTED`).
- `origin == analyst` with status verified, self_reported or third_party_reported:
  `<path>: origin analyst allows only inferred or not_found`.
- verified: when any cited source has origin auditor, `assurance` must be TESTED and `origin` must be
  auditor_procedure, regulator, registry or onchain
  (`<path>: verified with an auditor source requires assurance TESTED for this claim (curator Q8)`).
  The legal-field rule (regulator/registry/auditor/onchain) stays; an auditor source counts only when this rule passes.
- third_party_reported citing only auditor-origin independent sources requires `origin` independent_party or
  auditor_procedure (`<path>: auditor source: state origin (issuer statement -> self_reported; tested -> auditor_procedure)`).
- `assurance` non-null requires an auditor or independent (non-self, non-analyst) source in evidence
  (`<path>: assurance requires an auditor or independent source`).
- not_found: origin and assurance must be null (`<path>: not_found requires null origin and assurance`).

### 2.2 lib/validate.py (semantic errors; existing rules stay)
- Dense unique ids for R findings (the per-prefix rule covers G, D, C, U, R).
- Coded claims: "number" at interfaces[].amounts[].value; "ratio" at interfaces[].supply_concentration.ratio;
  deployment one-of.
- amounts (per entry, path `interfaces[i].amounts[j]`):
  - value.status != not_found (`...value: an amount entry needs a value; remove the entry instead`);
  - unit and scope non-empty after strip (`...unit: required`, `...scope: required`);
  - POSITION_VALUE needs valuation_basis (`...valuation_basis: required for POSITION_VALUE`);
  - OTHER needs a scope that is not MIGRATED_AMOUNT_SCOPE only at finalize (see 4.2), and in validate a scope of at
    least 20 characters (`...scope: OTHER needs an explicit definition (>= 20 characters)`);
  - block non-null requires chain non-null (`...chain: required when block is set`);
  - kind constraints: amounts allowed on L1_L2, L2_L3, within_L1, within_L2, sleeve_holding, reserve_lookthrough,
    asset_sale; RESERVE_LOOKTHROUGH only on reserve_lookthrough; SALE_PROCEEDS only on asset_sale;
    FACILITY_COMMITMENT and UNDRAWN_COMMITMENT only on L1_L2, L2_L3, within_L2
    (`...basis: <BASIS> not allowed on <kind>`).
- supply_concentration: only on L1_L2 (non-empty claim elsewhere -> error as other kind constraints); when ratio has a
  value: numerator, denominator non-empty and as_of non-null (`...supply_concentration: numerator, denominator and
  as_of are required with a ratio`).
- loan_identity, seller_of_record, buyer_of_record, repayment_source: asset_sale only (kind constraint as in 2.1).
- deployment: only on CORE_CREDIT and DEFI_LENDING strategies (LIQUIDITY_SLEEVE must be not_found without evidence);
  value DEPLOYED_VERIFIED requires status verified (`strategies[i].deployment: DEPLOYED_VERIFIED requires status
  verified`).
- findings:
  - scope_match by type: gap and structural_change -> not_applicable; discrepancy -> matched (or unchecked only while
    scope_note is a migration placeholder); scope_unresolved -> not_matched or unchecked; unreconciled_transaction ->
    any value except not_applicable. Error `findings[i].scope_match: <value> not allowed for <type>`.
  - discrepancy, scope_unresolved, unreconciled_transaction: scope_note non-empty (as 2.1 for discrepancy) and, unless
    scope_note is a migration placeholder, at least two assertions (`findings[i].assertions: at least two statements
    required for <type>`); every assertion source is in the finding's evidence (`findings[i].assertions[j].source:
    not in evidence`).
  - discrepancy subjects: at least one, and each must resolve to a claim (`findings[i].subjects[j]: <s> is not a
    claim`); resolution uses framework.resolve (3.6). Other types: subjects resolve to an object or a claim.
  - gap and structural_change: assertions empty.
  - resolution.status: gap/discrepancy/scope_unresolved/unreconciled_transaction -> open or resolved; structural_change
    -> not_applicable; resolved needs a non-empty note (`findings[i].resolution.note: required when resolved`).
  - k_checks and impact: no duplicates.
  - carried_from: unique across findings.

### 2.3 lib/lint.py (warnings)
`lint(doc)` returns six keys: address_warnings, layer_warnings, claim_warnings, path_warnings, amount_warnings,
provenance_warnings. Sorted, deterministic; `dd.py lint` prints the object.
- amount_warnings:
  - an amount whose value cites an onchain source without block or chain: `X2.amounts[0]: on-chain amount without
    block and chain`;
  - an amount with as_of null: `X5.amounts[0]: no observation time; it will not be counted`;
  - an L1_L2 or sleeve_holding interface with amounts but none of a countable basis (3.4): `X7: no countable basis
    (CURRENT_BALANCE, POSITION_VALUE, OUTSTANDING_PRINCIPAL)`;
  - CUMULATIVE_FUNDED whose scope mentions neither a period nor a date (no 4-digit year in scope):
    `X5.amounts[0]: CUMULATIVE_FUNDED scope should state the period`.
- provenance_warnings: a claim (status != not_found) citing a source with origin auditor and with origin null:
  `X5.terms: cites an auditor source; set origin and assurance (curator Q8)`.
- claim_warnings: add `T1.deployment: not set for a credit strategy` when a CORE_CREDIT or DEFI_LENDING strategy has
  deployment not_found without evidence.
- path_warnings: add a finding with blocking true, material false, k_checks empty and impact empty:
  `G4: blocking finding without k_checks or impact (section 1 cannot place it)`.

## 3. Framework view (lib/framework.py)

### 3.1 Flags and conflict statuses
`flag` unchanged except: a claim is CONFLICTING only when it is a subject of a discrepancy with scope_match matched
and resolution.status open. scope_unresolved and unreconciled_transaction findings never flag a claim; resolved
discrepancies never flag.
`conflict_status(finding)` -> CONFLICTING (open matched discrepancy), RESOLVED (resolved discrepancy),
SCOPE_UNRESOLVED (scope_unresolved), UNRECONCILED_TRANSACTION (unreconciled_transaction), or None (gap, structural).
`conflicts(doc)` -> rows `(finding id, conflict_status, scope_match, resolution status, subjects, assertion sources)`
for D, U and R findings in id order.

### 3.2 Claim ids
`claim_id(parts, doc)`: id-based path of a claim: the nearest ancestor with an id (E, P, T, X, Z) followed by the
field path, with `[n]` for array positions below it, e.g. `X2.amounts[0].value`, `X4.supply_concentration.ratio`,
`T1.default_path.loss_waterfall`, `P1.holder_rights.look_through`, `Z1.coverage`. Claims with no id ancestor use the
document path (`project.name`, `yield[0].gross_yield`, `onchain.contracts[2].proxy`). Deterministic and unique;
subject_path is reimplemented on top of it.

### 3.3 Chain lines, completeness, five questions
Unchanged except: five_questions gains a sixth row `Is deployment verified?` -> deployment `value [FLAG]` (UNRESOLVED
when not_found); asset_sale hop code becomes `[sale; <title_transfer value or ?>; loan <loan_identity flag>]`.

### 3.4 Allocation and counting (curator 4.1 aggregation rules)
`COUNTABLE = ("CURRENT_BALANCE", "POSITION_VALUE", "OUTSTANDING_PRINCIPAL")`.
`allocation(doc)` -> one row per amount entry on interfaces of kinds L1_L2, sleeve_holding, reserve_lookthrough,
asset_sale (strategy then interface id then entry index): `(strategy id, component, interface id, entry index, kind,
value or None, unit, basis, as_of, scope, counted bool, reason)`. Interfaces of these kinds without amounts give one row
with entry index None, reason `no amount`. `counted` is true only when all hold: kind L1_L2 or sleeve_holding; basis in
COUNTABLE; value has a value; as_of non-null; alternative.group null; scope not MIGRATED_AMOUNT_SCOPE. Reasons (first
that applies): `alternative A<n><o>`, `not a funding edge`, `basis <BASIS> not counted`, `no amount`, `no observation
time`, `migrated scope`, `counted`.
`total_key(row)` = (basis, unit, as_of date part YYYY-MM-DD, valuation_basis or ""). `allocation_totals(doc)` ->
per strategy, per component and per product (via strategy products; a strategy serving several products is listed
under each with the note `shared`), sums of counted values grouped by total_key, ordered by key. Two different keys are
never added together, and no code outside framework sums amounts. Totals are labelled `<sum> <unit> <BASIS> @<date>`.

### 3.5 Section 1 selection (curator Q10)
`critical(doc)` -> ordered finding ids for report section 1:
group 1 material true; group 2 blocking true with non-empty k_checks; group 3 blocking true with impact intersecting
SECTION1_IMPACTS. Each finding appears once (first group that matches). Within a group: priority ascending, then type
order R, D, U, G, C, then id. `critical_counts(doc)` -> (selected, total findings, open findings not selected).
No cap: all matching findings are returned; the renderer states the 5-8 target only as text (5.2).

### 3.6 resolve
`resolve(doc, path)` for subject and expectation paths: grammar
`^(@?(E|P|T|X|Z|G|D|C|U|R)[1-9][0-9]*)((\.[a-z][a-z0-9_]*)|(\[[0-9]+\]))*$`. `P<n>.holder_rights` maps to the
holder_rights entry of P<n>; `@<id>` selects the finding whose carried_from equals <id>, or the finding with that id
when none carries from it. Returns `(kind, node)` with kind claim, object, list or scalar; KeyError when not found.

## 4. Migration and seeding

### 4.1 lib/migrate.py
Add `convert_21(old, run)` (2.1 -> 2.2, pure, no classification invented):
- schema_version 2.2; run replaced by `run`; next_searches [].
- every claim gains origin null and assurance null.
- strategies: deployment empty not_found claim.
- interfaces: when the 2.1 amount claim has a value: `amounts = [AMOUNT(basis=MAP[old basis], value=old amount claim
  (+ origin/assurance null), unit=old currency value if it is a non-empty string else "n/d", as_of=None, block=None,
  chain=None, scope=MIGRATED_AMOUNT_SCOPE, valuation_basis=None)]`; otherwise `[]`. MAP: GROSS_FUNDED -> OTHER,
  COMMITMENT -> FACILITY_COMMITMENT, LOOKTHROUGH -> RESERVE_LOOKTHROUGH, RESERVE -> RESERVE_LOOKTHROUGH,
  SALE_PROCEEDS -> SALE_PROCEEDS, null -> OTHER. The old amount_basis is kept in the claim note when the note is empty:
  `2.1 basis <B>` (no note text otherwise changes).
- supply_concentration: ratio = empty not_found claim, but when the 2.1 claim had a value or evidence, ratio becomes
  not_found with the same evidence and note `migrated: <old value, truncated to fit 200 chars>`; numerator,
  denominator "" ; as_of, block, chain null.
- loan_identity, seller_of_record, buyer_of_record, repayment_source: empty not_found claims.
- findings: scope_match (gap, structural_change -> not_applicable; discrepancy -> unchecked; scope_unresolved ->
  unchecked); scope_note for discrepancy and scope_unresolved -> MIGRATED_NOTE_21 (the old note text is appended after
  ` -- ` when non-empty and not a placeholder, truncated to 200 chars total); assertions []; resolution {open, ""}
  (structural_change: {not_applicable, ""}); k_checks []; impact []; priority 2; carried_from = own id.
- Output passes validation with the same ledger (test with acme_v21 and with the three migrated real-run copies in the
  smoke step).
`migrate_to_current(old, run)`: 1.0 -> convert, convert_20, convert_21; 2.0 -> convert_20, convert_21; 2.1 ->
convert_21; 2.2 -> copy with run reset and next_searches emptied (run applied once in every chain).

### 4.2 lib/runstate.py
- `_seed_version` accepts 1.0, 2.0, 2.1 and 2.2.
- `finalize` refuses (ContractError, first offender in document order) when:
  `<D|U|R id>: scope not checked (scope_note is a migration placeholder)` for any finding whose scope_note starts with
  a MIGRATION_PLACEHOLDERS text; `X<n>.amounts[j]: amount scope not checked (migration placeholder)`;
  `QA failed: <QA ids>` when lib/qa reports any failure (6), with expectations from `audit/qa-expect.json` when it
  exists.
- Final outputs gain `<slug>.derived.json` (7.3). `ProjectDir.outputs()` includes it; amend archives it with the rest.
- `render_draft` and `finalize` pass qa results and the change log to the renderer.
- `log_name(state, kind, n)` helper returns `.scratch/logs/<run_id>-directives-r<n>.txt` or
  `.scratch/logs/<run_id>-amend-<n>.txt`; `dd.py status` prints both next names (`next_directives_log`,
  `next_amend_log`).

## 5. Review packet and report

### 5.1 lib/review.py
Sections in order:
```
# Review packet <slug> round <k>
## Coverage                  (as 2.1; claim counts by flag)
## Section 1 preview         critical(doc) entries: id | type | material | blocking | k_checks | impact | statement;
                             then `<selected> shown; <n> more open findings in section 6`
## Portfolio components      strategy | component | deployment | products | counted totals (3.4 labels)
## Framework completeness    CORE_CREDIT strategies only
## Three-layer chains        all strategies
## Amounts                   allocation rows: strategy | interface | entry | kind | value | unit | basis | as_of |
                             scope | counted | reason
## Alternative paths         per group: options with their interface ids
## Conflicts                 conflicts(doc) rows
## Provenance                claims with origin or assurance set: claim id | status | origin | assurance | sources
## QA                        qa results: id | rule | result | detail (expectations included)
## Migration checks pending  findings with placeholder scope notes; amounts with MIGRATED_AMOUNT_SCOPE
## Material findings / ## Blocking gaps / ## Other gaps / ## Discrepancies / ## Scope unresolved /
## Unreconciled transactions / ## Structural changes / ## Issuer requests / ## Proposed next searches /
## Directives template      (as now; the template's answer/drop lines accept G, D, U and R ids)
```

### 5.2 lib/render_md.py
Claim cell: `value [FLAG] (S1, S2) -- note`, and when origin or assurance is set:
`value [FLAG] (S1; origin issuer_management; assurance NOT_TESTED) -- note`.
Amount cell (one entry): `<value> <unit> <BASIS> @<as_of or n/d> [FLAG] (sources)`; scope on hover is not possible in
Markdown, so tables with amounts get a following `Amount scopes` list: `X2[0]: <scope>`. Several entries joined by
`; `.
Metadata table: add rows `Report generated` (run.finalized_at, or `draft` and the render clock date for drafts) and
`Data observed` (earliest and latest amount as_of, or `n/d`); `Started` stays. The two are never merged.
Sections (six reader sections stay; changes only):
```
1. Executive summary and critical findings
   - narrative.executive_summary
   - per CORE_CREDIT and DEFI_LENDING strategy: "### <strategy title>", the six-question table (3.3)
   - "Critical findings" -- critical(doc) in order, each: `[MATERIAL]`/`[BLOCKING]`/`[K1, K3]`/impact tags, id,
     conflict status when any, statement, evidence ids. Then the line
     `<selected> critical findings shown (target 5-8; all material items are always shown). <n> further open findings
     in section 6.`
2. Framework completeness and portfolio
   - completeness matrix; Portfolio components (with deployment column); Allocation table (3.4 rows); Totals by
     strategy, component and product (3.4 labels); line `Totals add only amounts with the same basis, unit and
     observation date; see Appendix N for the checks.`
3. Three-layer business model (as 2.1)
4. Capital allocation and credit deployment: amount column uses the amount cell; L1 -> L2 table adds supply
   concentration as `ratio [FLAG] (numerator / denominator @as_of, block, chain)`; Asset sales table columns:
   id | strategy | from -> to | loan identity | seller of record | buyer of record | legal transfer (title_transfer) |
   repayment source | servicer after exit (servicing) | recourse | retained exposure (residual_exposure) | amounts
5. Holder rights, default and recovery (as 2.1)
6. Material gaps and issuer requests: every open finding not in section 1, grouped: material, blocking, conflicts
   (D with conflict status), scope unresolved (U), unreconciled transactions (R), other gaps; each with id, statement,
   scope note, scope match, assertions (`S3 (2026-07-15): statement`), subjects, resolution; then issuer requests.
Appendix F. All findings: adds columns scope match, resolution, k_checks, impact, priority, carried from.
Appendix L. Legend: adds the nine bases with meanings, counting rule (3.4), origin and assurance values with the Q8
            rule, conflict statuses, deployment values.
Appendix N. Quantitative and provenance checks (QA results table, expectation results, rule texts from 6.1)
Appendix O. Changes since <seeded_from run id> (lib/changes, 7.2), or `No earlier run.`
```
Appendix order: A..M, then N, then O. Draft banner and final-run rules as now.

## 6. QA (lib/qa.py, `dd.py qa`)

### 6.1 Rules
`run(doc, expectations=None)` -> list of `{"id", "rule", "result": "pass"|"fail", "detail"}` in id order; detail lists
offending ids (sorted) or `ok`. Rules recompute from the document independently of allocation_totals and then compare.
```
QA1 basis       No total mixes amount bases, units, valuation bases or observation dates (each allocation_totals
                group recomputed from rows has one total_key; the recomputed sums equal the reported sums).
QA2 lookthrough No RESERVE_LOOKTHROUGH amount and no reserve_lookthrough interface is counted.
QA3 alternative No amount on an interface with an alternative group is counted.
QA4 proceeds    No SALE_PROCEEDS amount is counted; SALE_PROCEEDS amounts whose value status is not verified are
                listed in detail as unverified (pass, informational).
QA5 asof        No amount with as_of null is counted.
QA6 stockflow   No CUMULATIVE_FUNDED, FACILITY_COMMITMENT or UNDRAWN_COMMITMENT amount is counted or labelled
                outstanding in totals.
QA7 provenance  No claim citing an auditor source has origin null; no claim with an ISSUER_ORIGINS origin has status
                other than self_reported or not_found; no verified claim citing an auditor source lacks assurance TESTED.
QA8 conflicts   Every claim flagged CONFLICTING is a subject of an open discrepancy with scope_match matched and >= 2
                assertions; no scope_unresolved or unreconciled_transaction subject is flagged CONFLICTING.
QA9 placeholder No finding scope note and no amount scope is a migration placeholder.
QA10 section1   Every material finding and every blocking finding with k_checks is in critical(doc).
QA11 deployment No CORE_CREDIT or DEFI_LENDING strategy has deployment DEPLOYED_VERIFIED without status verified.
```
QA9 fails during seeded drafts by design (it lists what is still to check); finalize refuses on any failure.

### 6.2 Expectations (`--expect <file>`, default `audit/qa-expect.json` when it exists)
JSON array; each entry `{"id": "<1..20 chars>", "case": "<<=120 chars>", "path": "<resolve path>", "op": "<op>",
"value": <json>}`. Ops: `equals` (resolved value; a claim resolves to its value), `in` (value is a list), `status`
(claim status), `flag` (derived flag), `counted` (path `X<n>.amounts[j]`; bool), `exists` (bool), `not_contains`
(string value does not contain the given text, case-insensitive). Each gives a result
`{"id": "E:<id>", "rule": "<case>", "result", "detail": "<path> <op> <expected> -> <actual>"}` appended after QA11.
A malformed file or entry is a ContractError (exit 3) naming the entry. Expectation files are written by the analyst
(user) and saved verbatim; the agent never edits them (9.2).

### 6.3 CLI
`dd.py qa --slug <s> [--expect <file>] --root .` prints `{"results": [...], "failed": [ids]}`; exit 0 when none
failed, 5 when any failed (new exit code, documented in SKILL.md 9.2 and the dd.py help; references/runtime.md is not
touched).

## 7. Change log and derived output

### 7.1 Scope
Requirement: a compact change log linking each v2.1 issue or interface id to the revised field and evidence.

### 7.2 lib/changes.py
`diff(old_doc, new_doc)` where old_doc = `migrate_to_current(<archived record>, new_doc["run"])` read from
`archive/<run.seeded_from>/<slug>.dd.json` (when seeded_from is null or the file is missing: `[]` and the appendix text
`No earlier run.`). Compares by claim_id (3.2) and object ids, not by position. Rows
`{"ref", "path", "change": "added"|"removed"|"changed", "before", "after", "evidence_added"}` where before/after for a
claim are `value [status]` (value text truncated to 80 chars) and for other leaves the JSON value truncated to 80 chars.
Findings are matched by carried_from (a finding whose carried_from is U9 and id R1 gives a row
`ref U9 -> R1, path type, changed, scope_unresolved -> unreconciled_transaction`). Ignored paths: run.*, sources (only
`S<n> added` rows), next_searches, and any change that is exactly the migration itself (that is why old_doc is the
migrated record). Sorted by ref then path. `dd.py changes --slug <s> --root .` prints the rows as JSON.

### 7.3 `<slug>.derived.json` (final output, written by finalize; draft copy in .scratch/draft/)
```
{"derived_version": "rwa-dd-derived/1", "slug", "run_id", "schema_version", "skill_version",
 "record_sha256": <SHA-256 of the written <slug>.dd.json bytes>,
 "flags": {claim_id: flag, ...}                     (every claim, sorted by claim_id),
 "conflicts": [conflicts(doc) rows as objects],
 "critical": [ids], "critical_counts": {...},
 "allocation": [rows as objects], "totals": {...},
 "five_questions": {T<n>: [[q, a], ...]},
 "qa": [results], "changes": [rows]}
```
Deterministic (sorted keys, LF, UTF-8, two-space indent like the dd.json writer). Flags are derived output, not stored
in the record (D-rule unchanged); this file is how JSON consumers see traceable CONFLICTING claims.

## 8. scripts/dd.py
New subcommands `qa` and `changes` (6.3, 7.2). `lint` prints the six keys. `status` prints the two log names (4.2).
`init --seed-from` help: accepts records of schema 1.0, 2.0, 2.1 and 2.2. Exit code 5 = QA failure (qa only; finalize
uses ContractError exit 3 as for other refusals). Nothing else.

## 9. VERBATIM blocks

### 9.1 references/research-protocol.md
Each block replaces text found exactly once; if not found exactly once, STOP and report.

(a) Replace these four lines (the amounts bullet of section 1):
```
- Amounts: every funding edge records amount, currency and amount_basis (GROSS_FUNDED, COMMITMENT, LOOKTHROUGH,
  RESERVE, SALE_PROCEEDS). Only GROSS_FUNDED amounts on L1_L2 and sleeve_holding edges outside alternative groups are
  counted; everything else is linked, not summed. Pool supply concentration is recorded on the L1_L2 edge with chain,
  block or time observed; it never changes the route from POOL to DIRECT.
```
with
```
- Amounts (curator 4.1, Q9): record each number as an amounts entry with its measurement basis, unit, observation time
  (as_of: the time the value was observed in the source, never the report date), block and chain for on-chain reads,
  scope (population, period or account measured) and, for POSITION_VALUE, the valuation basis. Bases:
  CURRENT_BALANCE (token or asset holdings at the observation time), POSITION_VALUE (value of a position under a
  stated valuation basis), OUTSTANDING_PRINCIPAL (loan principal unpaid at the observation time; recorded unbilled
  principal goes here with the scope saying so), CUMULATIVE_FUNDED (actual disbursements over a stated period),
  FACILITY_COMMITMENT (contractual ceiling), UNDRAWN_COMMITMENT (unused part of it), SALE_PROCEEDS (proceeds actually
  received from a disposal), RESERVE_LOOKTHROUGH (an issuer's reserve or collateral assets, never additive), OTHER
  (only with a scope of at least 20 characters defining it). A sampled amount (for example an AUP loan sample) is
  CUMULATIVE_FUNDED or OUTSTANDING_PRINCIPAL with the sample, its date and the procedure in the scope; it is never the
  current portfolio. Keep token quantity and USD value as separate entries.
- Counting: only CURRENT_BALANCE, POSITION_VALUE and OUTSTANDING_PRINCIPAL amounts on L1_L2 and sleeve_holding edges,
  with an observation time and outside alternative groups, are counted, and totals add only amounts with the same
  basis, unit, valuation basis and observation date. Stocks are never added to flows, commitments or proceeds;
  look-through, alternatives and sale proceeds are never counted. An amount you cannot type is not counted.
- Pool supply concentration is recorded on the L1_L2 edge as a ratio with its numerator, denominator, observation time,
  block and chain; it never changes the route from POOL to DIRECT and is not borrower concentration.
- Deployment (curator P1): set each credit strategy's deployment: DEPLOYED_VERIFIED only when transfers into the
  credit arrangement are verified; DISCLOSED_UNVERIFIED when the issuer discloses the path but settlement is not shown;
  NOT_DEPLOYED or UNRESOLVED otherwise. No observed transfer in a sampled window does not prove that no funding path
  exists.
- interfaces[].as_of is the date the legal terms were observed; amounts carry their own observation times.
```

(b) Replace section `## 3. Where answers go` (heading line up to, not including, `## 4. Evidence rules`) with:
```
## 3. Where answers go
| Codes | Fields |
|---|---|
| A1, A6 | strategies[] (component, products, sublayers, business_type, deployment) |
| A2-A5 | entities[] (entity_class, functions with layer, role and evidence, registry facts), onchain.contracts[] for L1 control |
| B1-B3 | interfaces[] kind holder_L1, L1_L2, within_L1, sleeve_holding (route, legal_class, instrument, claim_holder, governing_law, amounts, supply_concentration, alternative) |
| B4 | redemption[], interfaces terms |
| C1-C4 | interfaces[] kind L2_L3, within_L2, within_L3, L3_L3O (method, legal_class, security, collateral, perfection, terms, amounts) |
| C5-C7 | strategies[].default_path, interfaces enforcement and recourse, supports[] (credit enhancement, yield support) |
| C8 (sales) | interfaces[] kind asset_sale (loan_identity, seller_of_record, buyer_of_record, title_transfer, repayment_source, servicing, recourse, residual_exposure, amounts SALE_PROCEEDS) |
| D1-D5 | holder_rights[] per product |
| E1-E4 | strategies[].l3_business, L3-O entities and L3_L3O interfaces |
| F1-F3 | flows (edges with view and interface) |
| Reserves | interfaces[] kind reserve_lookthrough (amounts RESERVE_LOOKTHROUGH) |
| Findings | findings[] (type, material, blocking, k_checks, impact, priority, scope_note, scope_match, assertions, subjects, resolution) |
Questions only the issuer can answer go to issuer_requests with the codes they answer; never to next_searches.
"C8 (sales)" and "Reserves" are table labels, not question codes; do not put them in issuer_requests answers.

```

(c) In section `## 4. Evidence rules`, insert after the bullet that begins `- Legal facts (entities, interfaces,` (that
whole bullet, up to the line before the next `- `) the following bullet:
```
- Provenance (curator Q8): origin says who asserted the fact; the cited sources are where it was published; assurance
  says what an auditor or reviewer tested for this precise claim. A management or issuer statement quoted in an AUP,
  attestation or third-party article is self_reported with origin issuer_management (or issuer_documents, borrower)
  and assurance NOT_TESTED when the publication is an auditor's. A fact the auditor itself inspected, reconciled or
  recalculated gets origin auditor_procedure and assurance TESTED, and only within the procedure's stated scope and
  date: an inspected security agreement confirms that the document was inspected, not that the security is perfected.
  Auditor branding never upgrades surrounding claims. Every claim that cites an auditor source sets origin and
  assurance.
```
If the anchor bullet is not found exactly once, STOP and report.

(d) Replace section `## 8. Findings and blocking gaps` (up to, not including, the next `## ` heading) with:
```
## 8. Findings and blocking gaps
- gap: a field that matters and is not_found. Blocking when it concerns the holders' legal counterparty (A2), the
  L1->L2 legal claim (B2), the L2->L3 security (C2), the loss waterfall (C6), holder look-through (D2) or the reality
  of the L3 business (E1), or who controls the assets or contracts.
- Every finding records k_checks (the K1-K7 framework checks it blocks), impact (credit_exposure, investor_rights,
  governance, capital_control, ownership, redemption, enforcement, security, recovery, liquidity) and priority 1-3
  (1 = decides the credit picture). Section 1 of the report shows material findings, blocking findings with k_checks
  and blocking findings on capital control, ownership, redemption, enforcement or security (curator Q10); everything
  else stays in section 6. Do not mark a finding material or blocking to move it into section 1.
- material: set material true for a finding the curator must see first (for example an outstanding position with a
  stale payment history). State only what the evidence shows: no event observed does not mean a loan is current, and
  a stale payment does not prove legal default or loss. Do not attribute a position to a product unless provenance and
  portfolio membership are shown. Pair it with an issuer request for reconciliation.
- discrepancy (CONFLICTING): two statements are shown to concern the same fact, date, parties and instrument and are
  incompatible. Set scope_match matched, record both statements as assertions (source, statement, as_of), name the
  conflicting claims as subjects (for example `X15.title_transfer`, `X2.amounts[0].value`) and write the scope note.
  Different documents, reporting dates, definitions or instruments alone are not a conflict.
- scope_unresolved: statements appear to differ but may cover different scopes, dates, products or contracts (for
  example a protocol agreement versus website terms). scope_match not_matched or unchecked; never flags a claim.
- unreconciled_transaction: accounts of one transaction (a sale, exit, refinancing, repayment) that are not reconciled.
  Record each account as an assertion and track loan identity, seller and buyer of record, legal transfer method,
  repayment source, servicer after exit and retained exposure on the asset_sale interface. Keep chain-of-funds
  observations and address-linkage hypotheses separate from claims of control, intent or misconduct; never conclude
  that a sale, assignment or misconduct occurred from on-chain observations alone. It never flags a claim.
- resolution: open until the evidence settles it; resolved needs a note saying what settled it. A finding re-typed in a
  seeded run keeps carried_from (the earlier id) so the change log links them.
- structural_change: the structure changed over time; record it also in history.
- A partnership announcement is not a deployed holding: keep it as a finding or issuer request until instruments and
  amounts are shown. An unidentified token or issuer stays unidentified: record balances and transfers as observed,
  not as a named instrument or as coupon income.
- No risk scores, no recommendations, no adjectives about quality.
```

### 9.2 SKILL.md
(a) Replace exactly these three lines
```
   `dd.py pdf-text` for PDFs. Edit `audit/dd.work.json` only; run `dd.py validate` until it exits 0, then
   `dd.py lint` and fix every warning (address, layer, claim and path warnings). In a run seeded from an earlier
   schema, check the scope note of every carried-over discrepancy: finalize refuses the migration placeholder.
```
with
```
   `dd.py pdf-text` for PDFs. Edit `audit/dd.work.json` only; run `dd.py validate` until it exits 0, then
   `dd.py lint` and fix every warning (address, layer, claim, path, amount and provenance warnings), then `dd.py qa`
   (exit 5 lists failed checks). In a run seeded from an earlier schema, re-check every carried-over amount (basis,
   unit, observation time, scope) and the scope note, scope match and assertions of every carried-over discrepancy and
   scope-unresolved finding: finalize refuses migration placeholders and failed checks. If the user supplies a
   regression expectations file, save it verbatim as `audit/qa-expect.json`; never edit it.
```
(b) Replace exactly the line
```
4. Save the user's reply verbatim to `.scratch/logs/directives-r<k>.txt` and run `dd.py directives --file <that file>`.
```
with
```
4. Save the user's reply verbatim to the `next_directives_log` path printed by `dd.py status`
   (`.scratch/logs/<run_id>-directives-r<k>.txt`) and run `dd.py directives --file <that file>`.
```
(c) Replace exactly the line
```
6. To correct a finalized run, save the user's amendment text verbatim to `.scratch/logs/amend-<n>.txt` and run
```
with
```
6. To correct a finalized run, save the user's amendment text verbatim to the `next_amend_log` path printed by
   `dd.py status` (`.scratch/logs/<run_id>-amend-<n>.txt`) and run
```
(d) Replace exactly the line
```
<root>/<slug>/   <slug>.dd.json, <slug>.report.md, <slug>.flow-<strategy>-<view>.svg  (final outputs, written only by finalize)
```
with
```
<root>/<slug>/   <slug>.dd.json, <slug>.derived.json, <slug>.report.md, <slug>.flow-<strategy>-<view>.svg
                 (final outputs, written only by finalize; derived.json holds flags, conflicts, totals, QA, changes)
```
Each of (a)-(d) must match exactly once; otherwise STOP and report. (Check the exact spacing of (d) in the file; if it
differs only in spaces, report the actual line in Block D and replace that line.)

### 9.3 references/schema.md
Regenerated by `dd.py schema-doc` (no hand edits).

### 9.4 docs/architecture.md (replace the whole file)
```
# rwa-due-diligence - Architecture

## Purpose
Read-only due diligence on an RWA private-credit project from its URL: map the project onto the Artemis three-layer
model, record entities, interfaces, holder rights, supports, default path, the underlying business, typed amounts and
fund flows as validated, evidence-linked data, and render a Markdown report, a derived-data file and diagrams from that
data. It does not score risk and never transacts.

## Research model (rwa-dd/2.2)
- Layers are functions inside one strategy, assigned by position in its financing chain: L1 On-chain Capital Vault,
  L2 Credit Financing Layer, L3 Underlying Business Layer, and the optional L3-O sub-layer for the L3's paying
  customers (contractual obligor, cash-flow source or offtaker). Legal entity, contract or pool, and economic role are
  separate objects.
- Strategy (T): one financing path from one or more products, with a component (core credit, liquidity sleeve or DeFi
  lending), business type, deployment status, sublayers, L3 business facts and the default path.
- Interface (X): one typed edge (holder to L1, L1 to L2, L2 to L3, L3 to L3-O, within a layer, sleeve holding, reserve
  look-through, asset sale) with route, legal claim class, financing method, the framework edge fields, typed amounts,
  pool supply concentration, sale reconciliation fields and an optional alternative-path tag.
- Amount: one measured number with its basis (current balance, position value, outstanding principal, cumulative
  funded, facility commitment, undrawn commitment, sale proceeds, reserve look-through, other), unit, observation time,
  block and chain, measured scope and valuation basis.
- Support (Z): credit enhancement or yield support as a cross-layer relationship.
- Holder rights per product; flows in three views (settlement, claim, repayment).
- Evidence: each claim has a status (six derived flags), the asserting origin, the publication sources and the
  assurance scope, so a statement quoted by an auditor is not mistaken for audited fact.
- Findings: gaps, discrepancies (same-scope conflicts that flag claims CONFLICTING), scope-unresolved items,
  unreconciled transactions and structural changes, each with scope match, assertions, resolution, framework checks,
  impact and priority; findings carried from an earlier run keep their earlier id.
- Counting: only stock amounts (balances, position values, outstanding principal) on funding edges, with an
  observation time and outside alternative paths, are summed, and only within the same basis, unit and date.
- Framework completeness K1-K7 and six questions per credit strategy (who holds, deploys, receives, repays,
  enforces, and whether deployment is verified).

## Modules
### Schema
- Responsibility: Define the rwa-dd/2.2 document, its enums, coded claims and field limits.
- Input: None.
- Output: The schema definition and its generated reference document.
- Depends on: none.

### Claims and validation
- Responsibility: Decide whether each claim is supported by its evidence and provenance and whether the document is
  consistent.
- Input: A DD document and its source ledger.
- Output: Errors with document paths, and lint warnings for layer, claim-class, path, amount, provenance and address
  issues.
- Depends on: Schema.

### Framework view
- Responsibility: Derive flags, conflict statuses, claim ids, completeness, chain lines, the six questions, the
  critical-findings selection and the allocation with its counting rule.
- Input: A valid DD document.
- Output: Per-claim flags, per-strategy checks and chains, allocation rows and totals, the section 1 selection.
- Depends on: Schema.

### Quality checks
- Responsibility: Assert the aggregation, provenance, conflict and placeholder rules and the analyst's regression
  expectations against a document.
- Input: A DD document and an optional expectations file.
- Output: Pass or fail results with offending ids.
- Depends on: Schema, Framework view.

### Change log
- Responsibility: List what changed between the record a run was seeded from and the current record.
- Input: The current document and the archived earlier record.
- Output: Change rows keyed by object, claim and carried-over finding ids.
- Depends on: Schema, Framework view, Migration.

### Migration
- Responsibility: Convert earlier-schema records into the current schema without inventing classifications.
- Input: An rwa-dd/1.0, 2.0 or 2.1 document.
- Output: An rwa-dd/2.2 document whose placeholders show what needs re-checking.
- Depends on: Schema.

### Run directory
- Responsibility: Own the per-project directory, the source ledger, the run state and the round lifecycle.
- Input: Analyst commands (init, init --seed-from, add-source, review, directives, qa, changes, finalize, amend).
- Output: Working files, review packets, directive records and final outputs in the project directory.
- Depends on: Schema, Claims and validation, Migration, Quality checks, Change log, Review loop, Reports, Flow diagrams.
- Note: Finalize refuses migration placeholders and failed quality checks.

### Review loop
- Responsibility: Summarise a round by evidence status, components, amounts, conflicts, provenance, checks and open
  items.
- Input: The working DD document; the analyst's directive text.
- Output: A review packet; parsed directives.
- Depends on: Schema, Framework view, Quality checks.

### Reports
- Responsibility: Render the DD document into a six-section reader report with detailed appendices, and the derived
  data file.
- Input: A valid DD document, round records, rejected searches, check results and the change log.
- Output: Markdown report linking one diagram per strategy and view; the derived JSON file.
- Depends on: Schema, Framework view, Quality checks, Change log, Flow diagrams.
- Note: HTML readers (a detailed curator edition and a short investor edition) are deferred until the data model is
  accepted.

### Flow diagrams
- Responsibility: Turn each strategy's flows into one diagram per view with fixed lanes and styles.
- Input: The flows section of a valid DD document.
- Output: One diagram per strategy and view.
- Depends on: Schema, Framework view.

### Research support
- Responsibility: Give the agent a written research method and two read-only helpers for public files.
- Input: The project URL and the analyst's directives.
- Output: Downloaded public files and their extracted text inside the project's scratch area.
- Depends on: Run directory.

## Known Limits
- Legal documents behind interfaces, holder rights, supports and default paths are rarely public; they enter through
  analyst add-source directives, and gaps stay visible as unresolved with issuer requests.
- Yield and size figures outside interface amounts keep a single observation date, not the full amount metadata.
- Diagrams need the external d2 binary at the pinned version; without it only draft reports can be produced.
- The framework and these data-model revisions are draft classification standards; the skill implements
  classification and evidence only, no risk methodology.

## Coding Notes
- The document is the single source of truth; renderers add only fixed headings, labels and the legend.
- Evidence flags, conflict statuses and amount totals are derived, never stored in the record; the derived file
  carries them for consumers.
- Timestamps are produced only by the script clock or copied from a source; the source ledger is append-only and
  authoritative.
- Nothing is written outside the project directory.
- Rendering is deterministic: identical input gives byte-identical output on every OS.
- Scripts are OS-neutral and use only the standard library unless a decision says otherwise.
```

## 10. Decisions (append to docs/decisions.md)
```
- D64 - Schema 2.2 - 2026-10-20 - rwa-dd/2.2 implements the curator's minor revision (Q8-Q10, v2.2 acceptance); 2.1 records are migrated by init --seed-from, never patched.
- D65 - Amount bases - 2026-10-20 - Interfaces carry typed amounts (nine bases, unit, observation time, block, chain, scope, valuation basis); GROSS_FUNDED is retired and migrates to OTHER with a placeholder scope that finalize refuses.
- D66 - Counting - 2026-10-20 - Only CURRENT_BALANCE, POSITION_VALUE and OUTSTANDING_PRINCIPAL on L1_L2 and sleeve_holding edges, with an observation time and outside alternatives, are summed, and only within one basis, unit, valuation basis and date.
- D67 - Provenance - 2026-10-20 - Claims carry origin and assurance; an issuer assertion is self_reported wherever it is published; verified via an auditor needs assurance TESTED (curator Q8).
- D68 - Conflicts - 2026-10-20 - A discrepancy flags claims CONFLICTING only with scope_match matched, two assertions and an open resolution; scope_unresolved and unreconciled_transaction never flag.
- D69 - Unreconciled transactions - 2026-10-20 - Finding type unreconciled_transaction (R) and asset_sale fields loan_identity, seller_of_record, buyer_of_record and repayment_source track unreconciled exits without conclusions.
- D70 - Deployment - 2026-10-20 - Credit strategies carry a deployment claim; DEPLOYED_VERIFIED needs status verified; it is shown in section 1.
- D71 - Observation times - 2026-10-20 - Amount observation time, interface legal as-of date and report generation time are separate fields and are never merged.
- D72 - Section 1 - 2026-10-20 - Section 1 shows material findings, blocking findings with k_checks and blocking findings on control, ownership, redemption, enforcement or security; target 5-8 without a cap; the rest stay in section 6 (curator Q10).
- D73 - QA - 2026-10-20 - lib/qa asserts the aggregation, provenance, conflict, placeholder, section 1 and deployment rules plus analyst expectations; finalize refuses on any failure.
- D74 - Change log - 2026-10-20 - A seeded run's report lists changes against the migrated earlier record, linking re-typed findings through carried_from.
- D75 - Derived output - 2026-10-20 - Finalize writes <slug>.derived.json with flags, conflicts, totals, the section 1 selection, QA results and changes, tied to the record by SHA-256.
- D76 - Run-scoped logs - 2026-10-20 - Directive and amendment logs are named with the run id so seeded runs never overwrite earlier logs.
```
Validation records, append:
`- 2026-10-20 - Curator review of v2.1 samples: Q8-Q10 decided; minor data-model revision implemented in v0.7.0.`

## 11. Fixtures and tests (offline)

### 11.1 Fixtures
- `git mv tests/fixtures/acme.dd.json tests/fixtures/acme_v21.dd.json` (stays 2.1, for migration tests).
- `tests/golden/acme_v21.migrated.json` = `convert_21(acme_v21, fixed run)` (state the fixed run in the test).
  Regenerate `acme_v1.migrated.json` and `acme_v2.migrated.json` only if the golden tests define them as
  migrate_to_current output; otherwise they stay byte-identical (say which in Block A).
- New `tests/fixtures/acme.dd.json` (2.2): start from the migrated acme_v21 and replace every placeholder, then add:
  - X2: two amounts: CURRENT_BALANCE (unit a token symbol, as_of a timestamp, block and chain, onchain source) and
    POSITION_VALUE (unit USD, valuation_basis text); supply_concentration ratio 0.5 with numerator, denominator,
    as_of, block, chain;
  - the T3 sleeve_holding: CURRENT_BALANCE; the reserve_lookthrough: RESERVE_LOOKTHROUGH; the L2_L3 commitment:
    FACILITY_COMMITMENT plus UNDRAWN_COMMITMENT; the alternative-group amount: CURRENT_BALANCE (proves alternatives
    are not counted); the asset_sale: SALE_PROCEEDS self_reported plus loan_identity inferred, seller_of_record and
    buyer_of_record self_reported, repayment_source not_found with evidence and note;
  - one CUMULATIVE_FUNDED amount on an L1_L2 interface with scope naming a sample and its date (not counted);
  - one CURRENT_BALANCE with as_of null on an L1_L2 interface (not counted; lint amount warning expected -- put this
    case in a test-local copy, not in the shared fixture, so the fixture lints clean);
  - one new auditor source (origin auditor) cited by two claims: one self_reported with origin issuer_management,
    assurance NOT_TESTED; one verified with origin auditor_procedure, assurance TESTED;
  - deployment on T1 (DEPLOYED_VERIFIED, verified, onchain source) and T2 (DISCLOSED_UNVERIFIED, self_reported);
  - findings: D1 matched with two assertions and a claim subject (open); D2 resolved with a note; U1 not_matched with
    two assertions; carried-over findings keep carried_from = their own id; re-type one carried-over finding (for
    example G3 -> a new R1, unreconciled_transaction, carried_from "G3", two assertions, subject the asset_sale
    interface) so the change log and `@G3` expectations have a case; k_checks and impact on the blocking gaps;
    priorities 1-3 used at least once each.
  The document validates against acme.sources.jsonl plus at most one new ledger line for the auditor source (extend
  the ledger fixture). `dd.py lint` returns no warnings; `dd.py qa` passes.
- `tests/fixtures/acme.qa-expect.json`: at least six expectations covering equals, in, status, flag, counted, exists,
  not_contains, one of them using `@<id>`.

### 11.2 Tests (new or changed; existing tests updated to 2.2)
- schema: enums; CLAIM_KEYS order; AMOUNT and finding fields; DateOrTimestamp accepts a date and a timestamp, rejects
  `2026-02-30` and `2026-10-20T25:00:00Z`; Int nullable; SUBJECT_PATTERN accepts `X2.amounts[0].value`; schema_doc
  matches references/schema.md.
- claims: every 2.1 error text with one passing and one failing case; Q8 cases: issuer origin + auditor source ->
  self_reported passes, third_party_reported fails, verified fails; auditor_procedure without assurance fails;
  verified with auditor source and NOT_TESTED fails; not_found with origin fails.
- validate: each new rule (2.2) with one passing and one failing case and exact error text.
- lint: one case per new warning kind; the fixture returns six empty lists.
- framework: claim_id for each kind of path; flags (open matched D flags, resolved D does not, U and R never);
  conflict_status values; allocation rows and reasons for every reason text; totals grouped by key (two dates of the
  same basis give two totals; CURRENT_BALANCE and POSITION_VALUE never summed); critical order and counts; resolve
  incl. `@` paths; six questions on T1 (exact pairs).
- qa: each rule passes on the fixture and fails on a minimal mutated copy (one mutation per rule; QA1 is tested by
  monkeypatching allocation_totals to merge two keys); expectations: each op pass and fail; malformed file -> exit 3.
- changes: diff of acme (2.2) against migrate_to_current(acme_v21): rows for changed amounts, a re-typed finding via
  carried_from, an added source; empty when seeded_from is null.
- migrate: acme_v21 -> golden byte-equal; GROSS_FUNDED -> OTHER with MIGRATED_AMOUNT_SCOPE and note `2.1 basis
  GROSS_FUNDED`; LOOKTHROUGH -> RESERVE_LOOKTHROUGH; supply_concentration evidence kept in ratio note; findings fields;
  output validates; 1.0 and 2.0 chains validate.
- runstate: seed from a 2.1 final run; finalize refuses each placeholder kind and a failing QA (with exact messages);
  finalize writes derived.json whose record_sha256 equals the written dd.json; amend archives derived.json; status
  prints log names with run_id.
- review: golden; section order of 5.1.
- render_md: golden; section 1 critical list and its count line; metadata rows `Report generated` and `Data observed`;
  Appendix N and O; legend lines for bases and Q8.
- directives: answer/drop accept U3 and R1.
- cli: `qa` exit codes 0/5; `changes` JSON; `lint` six keys.
- New test addresses use digit-only fakes (for example `0x1111111111111111111111111111111111111111`); existing tests
  stay as they are.

## 12. Build and verify (PowerShell, Local)
1. Canary 0.4. `git switch -c v070-measurement`.
2. Implement 1-11. Regenerate references/schema.md and goldens with a script under `.scratch/build/`.
3. `python -m pytest -q -rs` -> all pass, no d2 skips.
4. ast check (3.11) over scripts lib tests: OK.
5. Python scans, must find nothing: forbidden symbols (P1 list) in scripts, lib; network imports outside lib/fetch.py
   (AST); `subprocess` outside lib/flow.py; `shell=True`; `os.environ|getenv` in scripts, lib; bytes > 127 and CR in
   scripts lib tests references SKILL.md docs (binary fixtures excluded); any `render_html` reference; the string
   `GROSS_FUNDED` anywhere except lib/migrate.py, tests and docs/decisions.md.
6. Commit with a message file under .scratch\misc\: `feat: measurement, provenance and conflicts, schema rwa-dd/2.2
   (v0.7.0)`. `git show --stat HEAD` lists nothing under handoff_specs/. `git push -u origin v070-measurement`;
   `git ls-remote origin v070-measurement`.
7. Fresh clone of `v070-measurement` into `C:\web3projects\_v070fresh`; `python -m pytest -q -rs`; same counts; delete
   it.
8. Do NOT deploy. CChat verifies first; the owner deploys after acceptance.
9. Migration smoke with the repo code against copies only: delete `.scratch\build\smoke\` if it exists, copy
   `C:\web3projects\rwa-dd-reports\usd-ai`, `huma` and `hastra` into `.scratch\build\smoke\`; for each run
   `python scripts\dd.py init --slug <slug> --url <url> --seed-from --root .scratch\build\smoke`, then `validate`,
   `lint`, `qa`, `changes`, `review`; show for each: the init JSON, validate result, lint counts per key, the qa
   `failed` list (QA9 is expected to fail), the number of change rows (expected 0 before any research), and the
   "Section 1 preview", "Amounts" and "Migration checks pending" sections of the packet. Leave the smoke folder in
   place for CChat (it is under .scratch, ignored).
10. `git status --porcelain` shows only untracked entries under handoff_specs/.

### 12.1 Done criteria
- [ ] Tests pass in the working copy and the fresh clone; every golden listed and explained.
- [ ] Scans empty; only 0.3 files changed; nothing under handoff_specs/ committed.
- [ ] VERBATIM blocks exact; greps: `curator 4.1, Q9`, `Provenance (curator Q8)`, `unreconciled_transaction`,
      `Research model (rwa-dd/2.2)`, `rwa-dd/2.2` in references/schema.md, `amount and provenance warnings`,
      `next_directives_log`, `<slug>.derived.json`.
- [ ] Migration smoke: all three seeded copies validate; qa fails only on QA9 (report any other failure in Block D).
- [ ] Branch pushed; ls-remote equals HEAD.

## 13. Return contract
- **A** files table (added, changed, deleted, incl. every golden with reason); full lib/migrate.py convert_21 and
  migrate_to_current; the AMOUNT and finding schema parts; new claim, validator and lint rules with error texts;
  allocation reasons and total_key; critical() as implemented; lib/qa.py rule functions; changes.diff signature and
  matching rules; the exact asserted six-question pairs and the fixture's allocation rows.
- **B** pytest tails (working copy, fresh clone); ast; scans; smoke outputs per project.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.3: NONE".
- **D** anomalies (Benign / Needs decision / Not covered).

Also write Blocks A-D verbatim, exactly as in your reply, to `handoff_specs/results/handoff-module-v070.result.md`
(UTF-8, LF; overwrite on re-run). Never commit it.
