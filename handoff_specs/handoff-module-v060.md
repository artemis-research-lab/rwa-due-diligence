# handoff-module-v060 -- rwa-due-diligence v0.6.0: curator revisions (schema rwa-dd/2.1)

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. build the module in handoff_specs/handoff-module-v060.md"

## 0. Persistent context
- Read `docs/architecture.md` before executing; this spec replaces it (9.3).
- Base: `main` = `6b7deb94ab8e2769c4c392576756a8049a17f6a6` (v0.5.1 plus spec commit). Target: **SKILL_VERSION 0.6.0**,
  **SCHEMA rwa-dd/2.1**.
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v060-curator` from main, one commit, push it. Do not touch `main`. Do not commit anything under
  `handoff_specs/`.
- D1-D51 apply unless replaced below; this module adds D52-D63 (section 10).
- Scripts stay OS-neutral Python, standard library only (pypdf and d2 as before).

### 0.1 Why
The risk curator reviewed the v2 samples (usd-ai, huma, hastra; 2026-10-20) and gave conditional acceptance of the
architecture with these required corrections (curator documents: Data Model Revisions, Answers Q1-Q7, Substantive
Issues). Acceptance conditions for the next samples:
1. Hastra AUTO: X5 becomes POOL + PROTOCOL_ENTITLEMENT; no AP inferred for L1.
2. Hastra PRIME/AUTO: repo and live-rate alternatives are never counted twice.
3. USD.AI: GLX loan sale and capital recycling path is modelled.
4. USD.AI / Hastra: PYUSD and YLDS reserves are no longer forced into L2->L3 credit strategies.
5. Huma: PST, Institutional pools and the DeFi liquidity sleeve are distinguished.
6. Huma: the anomalous outstanding position is a material unresolved finding, with no unproven default conclusion.
7. Evidence: self-reported, third-party-reported and inferred are stored separately; conflicts are checked for same scope.
8. Flows and QA: legal, funding and repayment relations are traceable per path; unknown relations are marked; no double
   counting.
Curator decisions adopted: Q1 layer = strategy-specific function, legal entity / contract / role separate; Q2 L3-O is
an optional sub-layer with contractual obligor, cash-flow source and offtaker distinguished; Q3 sleeves stay in the
product allocation but outside core credit strategies; Q4 credit enhancement is a separate cross-layer relationship;
Q5 pool concentration never changes POOL to DIRECT; Q6 six evidence statuses; Q7 a six-section reader report with the
detail in appendices. No ratings, limits or thresholds.

### 0.2 Verified shared contracts (base commit)
```
lib/schema.py: ENUMS (claim_status verified|self_reported|inferred|not_found; evidence_flag 4 values; layer L1-L3;
  interface_kind holder_L1|L1_L2|L2_L3|within_L1|within_L2|within_L3; legal_class DL..EI,OTHER; method_code DL..PT;
  finding_type gap|discrepancy|structural_change; FINDING_PREFIX G/D/C); LEGAL_SECTIONS; CODED_CLAIMS;
  SUBJECT_PATTERN; DOCUMENT; skeleton(); order_like_schema(); iter_claims(); schema_doc(); SCHEMA_VERSION "rwa-dd/2.0"
lib/claims.py: LEGAL_VERIFIERS; evidence_role(source, claim) -> self|analyst|independent:<origin>; check_claim()
lib/framework.py: subject_path(parts, doc); conflicted(); flag(); flags(); SEVERITY; worst(); CHECKS K1-K7;
  completeness(); chain_line() (v0.5.1 position rules)
lib/migrate.py: FROM_VERSION "rwa-dd/1.0"; convert(old, run) -> 2.0
lib/runstate.py: _seed_version() accepts 1.0 and 2.0; _seeded_doc(); seed(); finalize() sets finalized_at but not
  skill_version (amend() does set it); RENDERERS md only; figures keyed T<n>-<view>
lib/lint.py: address_warnings(doc); scripts/dd.py lint prints {"address_warnings": [...]}
lib/review.py: groups A-F,O; completeness_table; chain_lines; render(doc, k)
lib/render_md.py: render(doc, rounds, figures, rejected); sections 1-17 + Appendices A-D (v0.5.1)
lib/flow.py: suffix letters C/P/U/U?/X; node layer pattern ^L[123]$
tests/fixtures: acme.dd.json (2.0, T1 P1, T2 P2, E1-E10, X1-X8, S1-S8 with origins first_party, regulator, registry,
  onchain, third_party, analyst, first_party, first_party; findings G1-G3, D1-D2, C1), acme_v1.dd.json (1.0)
```

### 0.3 File scope (HARD)
```
[EDIT] lib/schema.py, lib/claims.py, lib/validate.py, lib/framework.py, lib/migrate.py, lib/lint.py, lib/runstate.py,
       lib/review.py, lib/render_md.py, lib/flow.py, lib/textutil.py (helpers only), scripts/dd.py (lint output, help)
[EDIT] references/schema.md (regenerated), references/research-protocol.md (VERBATIM 9.1), docs/architecture.md
       (VERBATIM 9.3, whole file), docs/decisions.md (section 10), SKILL.md (VERBATIM 9.2)
[EDIT/NEW] tests/fixtures/acme.dd.json (2.1), tests/fixtures/acme_v2.dd.json (git mv of the current 2.0 fixture),
       tests/golden/* (regenerated; list every file), tests/golden/acme_v2.migrated.json (NEW), tests/unit/* as needed
[REUSE -- DO NOT TOUCH] lib/fetch.py, lib/pdftext.py, lib/ledger.py, lib/directives.py, assets/**, tools/**,
  references/runtime.md, references/third-party.md, references/source-registry.md, CLAUDE.md, .gitattributes,
  pytest.ini, .gitignore, handoff_specs/** (except the results file in section 12)
```

### 0.4 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-module-v060.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` =
`6b7deb94ab8e2769c4c392576756a8049a17f6a6`; `git status --porcelain` shows only untracked entries under
`handoff_specs/`; `python --version` >= 3.11; `d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. Schema rwa-dd/2.1 (lib/schema.py)

`SCHEMA_VERSION = "rwa-dd/2.1"`, `SKILL_VERSION = "0.6.0"`. Everything not listed stays as in 2.0.

### 1.1 Enums
```
claim_status += third_party_reported
evidence_flag = CONFIRMED, SELF_REPORTED, THIRD_PARTY_REPORTED, INFERRED, UNRESOLVED, CONFLICTING
layer += L3-O
role += contractual_obligor, cash_flow_source, offtaker_customer, loan_purchaser, protection_provider, reserve_assets
role -= ultimate_obligor            (migration maps it, 4.1)
interface_kind += L3_L3O, sleeve_holding, reserve_lookthrough, asset_sale
legal_class += PROTOCOL_ENTITLEMENT
method_code += OTHER
component: CORE_CREDIT, LIQUIDITY_SLEEVE, DEFI_LENDING
amount_basis: GROSS_FUNDED, COMMITMENT, LOOKTHROUGH, RESERVE, SALE_PROCEEDS
entity_class: legal_person, contract_or_pool, program, obligor_group, unknown
support_type: CREDIT_ENHANCEMENT, YIELD_SUPPORT
finding_type += scope_unresolved    (FINDING_PREFIX U)
```

### 1.2 Document changes (C = Claim)
```
strategies[]: + component: Enum component                      (after name)
entities[]:   + entity_class: Enum entity_class                (after id)
              functions[].layer: Enum layer, nullable
interfaces[]: + alternative: Obj(group Pattern ^A[1-9][0-9]*$ nullable, option Pattern ^[a-z]$ nullable)
              + amount: C          (coded: a number >= 0)
              + amount_basis: Enum amount_basis, nullable
              + supply_concentration: C
              + title_transfer: C, servicing: C, residual_exposure: C
supports: Arr of Obj(                                            (after holder_rights)
  id: Ref Z
  type: Enum support_type
  strategies: Arr(Ref T, min 1)
  provider: Ref E
  beneficiary: Ref E or P, nullable
  covered_exposure, trigger, coverage, exclusions, priority, enforceability, governing_law, holder_recourse: C)
findings[]: id Ref G|D|C|U; + material: Bool; + scope_note: Str(200)
flows.nodes[].layer: Pattern ^(L1|L2|L3|L3-O)$ nullable
```
`LEGAL_SECTIONS += "supports"`. `CODED_CLAIMS[("interfaces", "amount")] = (None, "number")` (shape "number": the value
is an int or float >= 0, not a bool). `SUBJECT_PATTERN` leading ids add `Z`: `^(E|P|T|X|Z)[1-9][0-9]*(\.[a-z][a-z0-9_]*){0,3}$`.
Key order: ... entities, interfaces, holder_rights, supports, yield ...
`MIGRATED_SCOPE_NOTE = "unchecked (migrated from rwa-dd/2.0)"` (constant used by migrate, review and finalize).
`schema_doc()` documents every addition, the six flags, the counting rule (3.4), and the holder-rights subject path
`P<n>.holder_rights.<field>` (carried over from v0.5.1 review). Regenerate references/schema.md.

## 2. Claims and validation

### 2.1 lib/claims.py
- `third_party_reported`: value non-null; at least one evidence source whose role is `independent:<origin>` (any
  origin; analyst is not independent). Allowed in legal paths too (it is not verification).
- `verified`, `self_reported`, `inferred`, `not_found`: unchanged.

### 2.2 lib/validate.py (semantic errors; existing rules stay)
- Dense unique ids for Z and for U findings (finding ids keep their per-type prefixes).
- References: supports[].strategies -> T, .provider -> E, .beneficiary -> E or P or null.
- `alternative`: group and option both null or both set; every group has >= 2 distinct options; all interfaces of
  one group belong to one strategy. Error texts: `interfaces[i].alternative: group and option must both be set or both
  null`, `alternative group A<n> needs at least two options`, `alternative group A<n> spans strategies`.
- `amount`: coded "number"; when amount.value is not null, amount_basis must not be null
  (`interfaces[i].amount_basis: required when amount has a value`).
- Kind constraints (claims must be not_found without evidence unless the kind matches):
  route -> L1_L2; method -> L2_L3 or L3_L3O; supply_concentration -> L1_L2;
  title_transfer, servicing, residual_exposure -> asset_sale.
- `from` may be a P id only for holder_L1 (unchanged); `from != to` (unchanged).
- findings: a `discrepancy` needs a non-empty scope_note (`findings[i].scope_note: required for a discrepancy`).
- functions[].layer may be null only when the role is one of: issuer, loan_purchaser, protection_provider,
  reserve_assets, auditor, other (`entities[i].functions[j].layer: required for role <role>`).
- Coverage rules: every product in >= 1 strategy; one holder_rights per product; >= 1 yield entry per product; every
  strategy with component CORE_CREDIT or DEFI_LENDING has a settlement flow edge (LIQUIDITY_SLEEVE is exempt).

### 2.3 lib/lint.py (warnings; `dd.py lint` prints all keys; SKILL says fix every warning)
`lint(doc)` returns `{"address_warnings": [...], "layer_warnings": [...], "claim_warnings": [...],
"path_warnings": [...]}`, each a list of `{"path", "message"}` (address warnings keep their current shape). Sorted,
deterministic. `scripts/dd.py lint` prints this object.
- layer_warnings: for layered kinds the `from`/`to` entity needs a function (strategy = the interface's or null) of the
  expected layer: holder_L1 (-, L1), L1_L2 (L1, L2), L2_L3 (L2, L3; an L1 `from` with an L2 function is fine),
  L3_L3O (L3, L3-O), within_Lk (Lk, Lk), sleeve_holding (L1, -). Message `X7: within_L2 but E1 has no L2 function for T2`.
- claim_warnings: an L1_L2 interface with route POOL whose legal_class value is DL, DI, AP or PI and none of whose
  legal_class evidence sources has source_type legal_doc: `X5: POOL with legal class AP needs a contract (legal_doc)
  source; use PROTOCOL_ENTITLEMENT or leave it not_found`.
- path_warnings: a CORE_CREDIT or DEFI_LENDING strategy without a holder_L1, without an L1_L2 (or L1-to-L2_L3) or
  without an L2_L3 interface; a LIQUIDITY_SLEEVE without sleeve_holding: `T3: no holder_L1 interface`.

## 3. Framework view (lib/framework.py)

### 3.1 Flags
`STATUS_FLAG`: verified CONFIRMED, self_reported SELF_REPORTED, third_party_reported THIRD_PARTY_REPORTED, inferred
INFERRED, not_found UNRESOLVED; CONFLICTING when conflicted (discrepancy subjects only; `scope_unresolved` findings
never make a claim CONFLICTING). `SEVERITY` (worst first): CONFLICTING, UNRESOLVED, INFERRED, THIRD_PARTY_REPORTED,
SELF_REPORTED, CONFIRMED. `subject_path` handles supports: claims under supports[i] -> `Z<n>.<field>`.

### 3.2 Completeness
K1-K7 unchanged, computed only for strategies with component CORE_CREDIT.

### 3.3 Chain lines
Extend the v0.5.1 rules (positions, continuations, starts, labels, cycle guard, depth-first id order):
```
kind                 from position -> to position     hop code
holder_L1            P   -> L1                         [legal_class]
L1_L2                L1  -> L2                         [route; legal_class]
sleeve_holding       L1  -> issuer                     [legal_class]
L2_L3                L2  -> L3  (and L1 with L2 fn)    [method; security]
L3_L3O               L3  -> L3-O                       [legal_class]
asset_sale           L2  -> transferee                 [sale; <title_transfer value or ?>]
reserve_lookthrough  issuer -> reserve                 [look-through]
within_Lk            Lk  -> Lk                         [legal_class]
```
Continuations: L1: within_L1, L1_L2, sleeve_holding, (L2_L3 with L2 function); L2: within_L2, L2_L3, asset_sale;
L3: within_L3, L3_L3O; issuer: reserve_lookthrough; L3-O, transferee, reserve: none. Starts: holder_L1, then unused
L1_L2, L2_L3, sleeve_holding, asset_sale (in that order, id order within each). Labels: `(L1)`, `(L2)`, `(L3)`,
`(L3-O)`, `(L1/L2)`, `(issuer)`, `(reserve)`, `(transferee)`. When an interface has an alternative, append
`; alt A<n><option>` inside its hop brackets (e.g. `[REPO; secured; alt A1a]`). The v0.5.1 within_L3 + ultimate_obligor
rule is replaced by the L3_L3O kind.

### 3.4 Allocation and counting
`allocation(doc)` -> rows `(strategy id, component, interface id, kind, amount value or None, currency value or None,
basis or None, counted bool, reason)` for every interface of kinds L1_L2, sleeve_holding, reserve_lookthrough,
asset_sale, in strategy then interface id order. `counted` is true only when kind is L1_L2 or sleeve_holding, basis is
GROSS_FUNDED, amount has a value and alternative.group is null. Reasons (first that applies): `alternative A<n><o>`,
`basis <BASIS>`, `no amount`, `not a funding edge`, `counted`. `allocation_totals(doc)` -> per strategy and per
component, sums of counted amounts grouped by currency value (`n/d` when currency is null). No other code sums amounts.

### 3.5 Five questions
`five_questions(doc, strategy_id)` for CORE_CREDIT strategies -> five `(question, answer)` pairs:
```
Who holds investor capital?   `to` entities of holder_L1 interfaces
Who deploys credit?           `to` entities of L1_L2 interfaces, plus L1 entities that are `from` of L2_L3
Who receives financing?       `to` entities of L2_L3 interfaces
Who must repay?               the same L3 entities, then `to` entities of L3_L3O as "cash flows from: ..."
Who can enforce the claim?    holder_rights.claim_against values of the strategy's products, then enforcement values
                              of the strategy's L2_L3 interfaces
```
Entity answers use the chain-line node label plus the flag of the interface's legal_class claim in brackets, joined
by "; " in interface-id order without duplicates; claim answers use `value [FLAG]`. `UNRESOLVED` when empty.
Interfaces in alternative groups are shown with their `alt` tag.

## 4. Migration and seeding

### 4.1 lib/migrate.py
Keep `convert` (1.0 -> 2.0) and add `convert_20(old, run)` (2.0 -> 2.1, pure, no classification invented):
- schema_version 2.1; run replaced by `run`; next_searches [].
- strategies: component CORE_CREDIT.
- entities: entity_class `unknown`. A function with role ultimate_obligor becomes layer `L3-O`, role
  `cash_flow_source` (the weakest reading; the analyst upgrades it with evidence).
- interfaces: a within_L3 interface whose `to` entity had an ultimate_obligor function for the interface's strategy or
  null becomes kind L3_L3O. Every interface gains alternative {group null, option null}, amount / supply_concentration /
  title_transfer / servicing / residual_exposure as empty not_found claims, amount_basis null.
- supports [].
- findings: material false; scope_note = MIGRATED_SCOPE_NOTE for discrepancies, "" otherwise.
- claim statuses unchanged (the analyst re-labels third-party-reported claims in the seeded run).
- Output passes validation with the same ledger (test with acme_v2 and with the three migrated real-run copies in the
  smoke step).
`migrate_to_current(old, run)`: 1.0 -> convert then convert_20 (run applied once); 2.0 -> convert_20; 2.1 -> copy with
run reset and next_searches emptied.

### 4.2 lib/runstate.py
- `_seed_version` accepts rwa-dd/1.0, 2.0 and 2.1; `_seeded_doc` uses `migrate_to_current`.
- `finalize` sets `run.skill_version = schema.SKILL_VERSION` (finals of 2026-10-20 recorded 0.5.0 though rendered by
  0.5.1) and refuses with ContractError `D<n>: scope not checked (scope_note is the migration placeholder)` while any
  discrepancy has scope_note == MIGRATED_SCOPE_NOTE.
- Figures: diagrams for every (strategy, view) with edges, as now.

## 5. Review packet (lib/review.py)
Sections in order:
```
# Review packet <slug> round <k>
## Coverage                  columns: group | CONFIRMED | SELF_REPORTED | THIRD_PARTY_REPORTED | INFERRED | UNRESOLVED |
                             CONFLICTING; groups as now plus S supports
## Portfolio components      strategy | component | products | counted total (per currency)
## Framework completeness    CORE_CREDIT strategies only
## Three-layer chains        all strategies
## Allocation                the allocation rows (3.4): strategy | interface | kind | amount | basis | counted | reason
## Alternative paths         per group: options with their interface ids
## Material findings         findings with material true
## Scope checks pending      discrepancies whose scope_note is the migration placeholder
## Blocking gaps / ## Other gaps / ## Discrepancies (with scope note) / ## Scope unresolved / ## Structural changes
## Issuer requests / ## Proposed next searches / ## Directives template      (as now)
```

## 6. Markdown report (lib/render_md.py) -- reader structure (curator Q7)

`render(doc, rounds=(), figures=None, rejected=())`. Claim cell: `value [FLAG] (S1, S2) -- note` with the six flags.
Sections, in order (nothing else):
```
metadata table (as now)
1. Executive summary and critical findings
   - narrative.executive_summary
   - per CORE_CREDIT strategy: "### <strategy title>" and the five-questions table (3.5)
   - Material findings (material true), then blocking gaps, each with [MATERIAL] / [BLOCKING]
2. Framework completeness and portfolio
   - completeness matrix (CORE_CREDIT)
   - Portfolio components table: strategy | component | products | business type | counted total
   - Allocation table (3.4)
3. Three-layer business model
   - per strategy: component, products, business type, sublayers, chain lines
   - Functions by entity: entity | class | layer | role | strategy | evidence
4. Capital allocation and credit deployment
   - L1 -> L2 (holder_L1, L1_L2, within_L1): id | strategy | from -> to | route | legal class | counterparty |
     instrument | claim holder | amount | basis | supply concentration | alternative | terms | governing law
   - L2 -> L3 (L2_L3, within_L2, within_L3, L3_L3O): id | strategy | from -> to | method | legal class | counterparty |
     security | collateral | perfection | enforcement | recourse | amount | alternative | terms
   - Liquidity sleeves (sleeve_holding, reserve_lookthrough): id | strategy | from -> to | legal class | instrument |
     amount | basis | terms
   - Asset sales (asset_sale): id | strategy | from -> to | title transfer | servicing | recourse | amount | basis |
     residual exposure
5. Holder rights, default and recovery
   - holder rights per product (nine fields)
   - default and recovery path per CORE_CREDIT strategy (events of default, enforcement, ordered loss waterfall,
     recovery history)
   - supports: id | type | strategies | provider | beneficiary | covered exposure | trigger | coverage | exclusions |
     priority | enforceability | governing law | holder recourse
6. Material gaps and issuer requests
   - Material and blocking gaps, scope unresolved, discrepancies (each with scope note), issuer requests
Appendix A. Legal entity register (as old section 4, plus entity class)
Appendix B. L3 business (per CORE_CREDIT strategy, seven fields)
Appendix C. Fund flows (per strategy and view: image link, then edge table)
Appendix D. Yield, fees and redemption
Appendix E. On-chain contracts and control
Appendix F. All findings (gaps, discrepancies, scope unresolved, structural changes, open questions)
Appendix G. History
Appendix H. Audits and size
Appendix I. Sources
Appendix J. Analyst interventions
Appendix K. Unmapped facts
Appendix L. Legend (six flags with their definitions from 9.1 section 4, layers incl. L3-O and its three roles,
            route/method/legal-class codes incl. PROTOCOL_ENTITLEMENT, components, amount bases, counting rule,
            alternative tag, flow views, lanes, diagram suffixes)
Appendix M. Searches not run (final runs only)
```
Draft banner and final-run rules as now.

## 7. Flow diagrams (lib/flow.py)
Status suffixes: CONFIRMED ` [C]`, SELF_REPORTED ` [S]`, THIRD_PARTY_REPORTED ` [T]`, INFERRED ` [I]`, UNRESOLVED
` [U]` (` [U?]` when not_found without evidence), CONFLICTING ` [X]`; opacity 0.7 for S, T, I and 0.5 for U. Node
layer accepts L3-O. Layout unchanged.

## 8. scripts/dd.py
`lint` prints the 2.3 object. `init --seed-from` help says it accepts records of schema 1.0, 2.0 and 2.1. Nothing else.

## 9. VERBATIM blocks

### 9.1 references/research-protocol.md
Replace each block below; each anchor is the section heading line up to (not including) the next `## ` heading.
If any heading is not found exactly once, STOP and report.

Replace section `## 1. The model` with:
```
## 1. The model
- Layers are functions inside one strategy, assigned by position in that strategy's financing chain, never by an
  entity's industry (curator decision Q1, 2026-10-20). Legal entity, contract or pool, and economic role are separate
  objects; establish each role on its own transaction evidence.
  - L1 On-chain Capital Vault: the vault and the legal person that owns its assets and faces the holders. Record the
    vault contract, protocol operator, token issuer and holders' legal counterparty separately; never assume they are
    the same legal person, and never equate a wallet, program or pool contract with a legal person.
  - L2 Credit Financing Layer: the credit provider to the operating business (pool, fund, lender of record, warehouse
    SPV, trust, servicer, security agent). A lender that lends on to operating businesses is L2.
  - L3 Underlying Business Layer: the borrower that receives the financing and runs the business. A lending company
    that borrows from an L2 arrangement is L3.
  - L3-O (optional): parties downstream of L3 whose payments repay it. Role contractual_obligor only when a document
    shows they legally owe L3; cash_flow_source for business cash flows (for example merchants' settlement fees);
    offtaker_customer for buyers of goods, services or compute. Link them with L3_L3O interfaces.
- entity_class: legal_person, contract_or_pool, program, obligor_group or unknown. A pool or program is never treated
  as a liable legal person.
- Each strategy (T) has a component: CORE_CREDIT (an underlying real-world financing business), LIQUIDITY_SLEEVE
  (undeployed cash or stablecoin) or DEFI_LENDING (lending-market supply with protocol-enforced entitlements). Never
  invent an L3 for a sleeve: link the held instrument's issuer with sleeve_holding and its backing assets with
  reserve_lookthrough (amount basis LOOKTHROUGH or RESERVE).
- Credit enhancement and yield support are supports (Z), not interfaces: provider, beneficiary, covered exposure,
  trigger, coverage, exclusions, priority, enforceability, governing law, holder recourse. Never assume a holder has
  recourse against a warrantor or reinsurer, and never place a support in a loss waterfall before its claim path is
  shown.
- Loan sales after origination (season and sell) are asset_sale interfaces from the selling lender to the transferee
  (role loan_purchaser), with title transfer, servicing, recourse, proceeds (amount basis SALE_PROCEEDS) and residual
  exposure. A transferee is not a new L3. Do not assume every sale belongs to the live portfolio.
- Competing legal paths for one position (for example historical repo terms and current live-rate terms) are
  alternatives: the same alternative group, different option letters. They are never parallel exposures.
- Amounts: every funding edge records amount, currency and amount_basis (GROSS_FUNDED, COMMITMENT, LOOKTHROUGH,
  RESERVE, SALE_PROCEEDS). Only GROSS_FUNDED amounts on L1_L2 and sleeve_holding edges outside alternative groups are
  counted; everything else is linked, not summed. Pool supply concentration is recorded on the L1_L2 edge with chain,
  block or time observed; it never changes the route from POOL to DIRECT.
- A product may feed several strategies; a strategy may serve several products. Pure principal commodity purchase and
  resale (PT) is trade finance: business_type trade_finance_pt or mixed.
```

Replace section `## 4. Evidence rules` with:
```
## 4. Evidence rules
- Register every fetch attempt with add-source, including failures. A checked-and-absent fact is not_found WITH that
  evidence.
- origin is about who produced the source: first_party, regulator, registry (company, lien and fund registries,
  GLEIF), auditor, onchain (chain state, a block explorer or an indexer reading it), third_party, analyst.
- Set publisher to the entity id when a source is published by an entity in the document; set subject on a claim when
  it is about one entity or product. A source never verifies claims about its own publisher.
- Six statuses, kept distinct in the data (curator decision Q6): verified (CONFIRMED: direct, sufficient evidence for
  the precise claim within its stated scope); self_reported (issuer, protocol, borrower or another interested party);
  third_party_reported (a third party reports it; its scope and authority still need assessing); inferred (your
  conclusion from cited facts; the note states the reasoning); not_found (UNRESOLVED); CONFLICTING is derived from
  discrepancy subjects.
- Legal facts (entities, interfaces, holder_rights, supports, eligibility) are verified only by regulator, registry,
  auditor or onchain sources, and only within the scope those sources cover. On-chain confirmation of pool receipts
  confirms the receipt balances, not the off-chain lender of record or the holder's rights against a borrower; never
  upgrade a claim because an adjacent token transfer is confirmed. An analyst source never appears in the evidence of
  a verified claim.
- Never assign an entity to a layer, or an interface to a route, method or legal class, without a source: leave the
  claim not_found with the sources checked, and add an issuer request.
- Route and legal claim are separate questions (curator Constraint 1): a pool supply is not a loan to the pool
  operator; a pool receipt is PROTOCOL_ENTITLEMENT unless a contract shows more; a fund subscription is not a loan to
  the fund; a vault share or position NFT is not a participation in the borrower debt without the participation
  agreement; AP or PI at a lower layer never gives an upstream holder the same title. Traverse each legal edge and keep
  unverified steps visible instead of collapsing them into one direct claim.
- Name the subjects of every discrepancy (for example `X3.security`, `T1.default_path.loss_waterfall`,
  `T2.l3_business.performance`, `P1.holder_rights.look_through`, `Z1.coverage`) and write its scope note: why both
  statements concern the same fact, timeframe and contractual scope. When the documents may simply cover different
  scopes or dates, record a scope_unresolved finding instead. Never point an interface at its own source entity.
- Chain state outranks project docs on permissions, gating, roles and admin control; contract-level access and legal
  eligibility are separate claims.
- Quote the shortest verbatim excerpt that supports the claim (<= 300 chars). Never paraphrase into the excerpt.
```

Replace section `## 8. Findings and blocking gaps` with:
```
## 8. Findings and blocking gaps
- gap: a field that matters and is not_found. Blocking when it concerns the holders' legal counterparty (A2), the
  L1->L2 legal claim (B2), the L2->L3 security (C2), the loss waterfall (C6), holder look-through (D2) or the reality
  of the L3 business (E1), or who controls the assets or contracts.
- material: set material true for a finding the curator must see first (for example an outstanding position with a
  stale payment history). State only what the evidence shows: no event observed does not mean a loan is current, and
  a stale payment does not prove legal default or loss. Do not attribute a position to a product unless provenance and
  portfolio membership are shown. Pair it with an issuer request for reconciliation.
- discrepancy: two sources disagree about the same fact, timeframe and scope; cite both, name the subjects, write the
  scope note. scope_unresolved: two documents appear to differ but may cover different scopes, dates or products;
  cite both; it never makes a claim CONFLICTING. structural_change: the structure changed over time; record it also in
  history.
- A partnership announcement is not a deployed holding: keep it as a finding or issuer request until instruments and
  amounts are shown.
- No risk scores, no recommendations, no adjectives about quality.
```

### 9.2 SKILL.md
Replace exactly the line
```
   `dd.py pdf-text` for PDFs. Edit `audit/dd.work.json` only; run `dd.py validate` until it exits 0, then
```
and the following line
```
   `dd.py lint` and fix every warning.
```
with
```
   `dd.py pdf-text` for PDFs. Edit `audit/dd.work.json` only; run `dd.py validate` until it exits 0, then
   `dd.py lint` and fix every warning (address, layer, claim and path warnings). In a run seeded from an earlier
   schema, check the scope note of every carried-over discrepancy: finalize refuses the migration placeholder.
```
If the two original lines are not found exactly once as a pair, STOP and report.

### 9.3 docs/architecture.md (replace the whole file)
```
# rwa-due-diligence - Architecture

## Purpose
Read-only due diligence on an RWA private-credit project from its URL: map the project onto the Artemis three-layer
model, record entities, interfaces, holder rights, supports, default path, the underlying business and fund flows as
validated, evidence-linked data, and render a Markdown report and diagrams from that data. It does not score risk and
never transacts.

## Research model (rwa-dd/2.1)
- Layers are functions inside one strategy, assigned by position in its financing chain: L1 On-chain Capital Vault,
  L2 Credit Financing Layer, L3 Underlying Business Layer, and the optional L3-O sub-layer for the L3's paying
  customers (contractual obligor, cash-flow source or offtaker). Legal entity, contract or pool, and economic role are
  separate objects.
- Strategy (T): one financing path from one or more products, with a component (core credit, liquidity sleeve or DeFi
  lending), business type, sublayers, L3 business facts and the default path.
- Interface (X): one typed edge (holder to L1, L1 to L2, L2 to L3, L3 to L3-O, within a layer, sleeve holding, reserve
  look-through, asset sale) with route, legal claim class (incl. protocol entitlement), financing method, the framework
  edge fields, amount and amount basis, supply concentration, sale fields and an optional alternative-path tag.
- Support (Z): credit enhancement or yield support as a cross-layer relationship with provider, beneficiary, coverage,
  trigger, priority and enforceability.
- Holder rights per product: instrument nature, claim against, look-through, recourse, law, forum, insolvency
  protection, disclaimers.
- Flows: one node set, three views (settlement, claim, repayment), each edge tagged with strategies and interface.
- Evidence: six statuses kept distinct (confirmed, self-reported, third-party-reported, inferred, unresolved,
  conflicting); flags are derived, never entered by hand; conflicts require a same-scope note.
- Counting: only gross funded amounts on funding edges outside alternative paths are summed; look-through, reserves,
  commitments and sale proceeds are linked, not added.
- Framework completeness K1-K7 per core credit strategy; five questions per core credit strategy (who holds, deploys,
  receives, repays, enforces).

## Modules
### Schema
- Responsibility: Define the rwa-dd/2.1 document, its enums, coded claims and field limits.
- Input: None.
- Output: The schema definition and its generated reference document.
- Depends on: none.

### Claims and validation
- Responsibility: Decide whether each claim is supported by its evidence and whether the document is consistent.
- Input: A DD document and its source ledger.
- Output: Errors with document paths, and lint warnings for layer, claim-class, path and address issues.
- Depends on: Schema.

### Framework view
- Responsibility: Derive flags, completeness, chain lines, the five questions and the allocation with its counting rule.
- Input: A valid DD document.
- Output: Per-claim flags, per-strategy checks and chains, allocation rows and totals.
- Depends on: Schema.

### Migration
- Responsibility: Convert earlier-schema records into the current schema without inventing classifications.
- Input: An rwa-dd/1.0 or 2.0 document.
- Output: An rwa-dd/2.1 document whose placeholders show what needs re-checking.
- Depends on: Schema.

### Run directory
- Responsibility: Own the per-project directory, the source ledger, the run state and the round lifecycle.
- Input: Analyst commands (init, init --seed-from, add-source, review, directives, finalize, amend).
- Output: Working files, review packets, directive records and final outputs in the project directory.
- Depends on: Schema, Claims and validation, Migration, Review loop, Reports, Flow diagrams.
- Note: Finalize refuses discrepancies whose scope was never checked after migration.

### Review loop
- Responsibility: Summarise a round by evidence status, components, completeness, allocation and open checks.
- Input: The working DD document; the analyst's directive text.
- Output: A review packet; parsed directives.
- Depends on: Schema, Framework view.

### Reports
- Responsibility: Render the DD document into a six-section reader report with detailed appendices.
- Input: A valid DD document, the round records and the rejected searches.
- Output: Markdown report linking one diagram per strategy and view.
- Depends on: Schema, Framework view, Flow diagrams.
- Note: HTML output is suspended until the reader structure is settled.

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
- Diagrams need the external d2 binary at the pinned version; without it only draft reports can be produced.
- The framework and these data-model revisions are draft classification standards; the skill implements
  classification and evidence only, no risk methodology.

## Coding Notes
- The document is the single source of truth; renderers add only fixed headings, labels and the legend.
- Evidence flags and amount totals are derived, never stored.
- Timestamps are produced only by the script clock; the source ledger is append-only and authoritative.
- Nothing is written outside the project directory.
- Rendering is deterministic: identical input gives byte-identical output on every OS.
- Scripts are OS-neutral and use only the standard library unless a decision says otherwise.
```

## 10. Decisions (append to docs/decisions.md)
```
- D52 - Schema 2.1 - 2026-10-20 - rwa-dd/2.1 implements the curator's data-model revisions; 2.0 records are migrated by init --seed-from, never patched.
- D53 - Components - 2026-10-20 - Strategies carry a component (CORE_CREDIT, LIQUIDITY_SLEEVE, DEFI_LENDING); completeness and the five questions apply to core credit only; sleeves never get an invented L3.
- D54 - Protocol entitlement - 2026-10-20 - PROTOCOL_ENTITLEMENT is a legal claim class for pool receipts; a POOL route with DL, DI, AP or PI needs a contract source (lint).
- D55 - Alternatives - 2026-10-20 - Competing legal paths share an alternative group and are excluded from counting.
- D56 - Amounts - 2026-10-20 - Funding edges record amount and amount basis; only gross funded amounts outside alternatives are summed.
- D57 - Supports - 2026-10-20 - Credit enhancement and yield support are supports (Z), not interfaces or waterfall steps.
- D58 - Asset sales - 2026-10-20 - Loan sales after origination are asset_sale interfaces; a transferee is not an L3.
- D59 - L3-O - 2026-10-20 - L3-O is a layer value with roles contractual_obligor, cash_flow_source and offtaker_customer, linked by L3_L3O interfaces; migration maps ultimate_obligor to cash_flow_source.
- D60 - Six statuses - 2026-10-20 - Claim status adds third_party_reported; flags are CONFIRMED, SELF_REPORTED, THIRD_PARTY_REPORTED, INFERRED, UNRESOLVED, CONFLICTING.
- D61 - Scope checks - 2026-10-20 - A discrepancy needs a same-scope note; scope_unresolved findings never flag claims; finalize refuses migrated placeholders.
- D62 - Material findings - 2026-10-20 - Findings carry a material flag; material findings open the report.
- D63 - Reader report - 2026-10-20 - The Markdown report has six reader sections (curator Q7) with detail in appendices A-M.
```
Validation records, append:
`- 2026-10-20 - Curator review of v2 samples: architecture accepted conditionally; revisions implemented in v0.6.0.`

## 11. Fixtures and tests (offline)

### 11.1 Fixtures
- `git mv tests/fixtures/acme.dd.json tests/fixtures/acme_v2.dd.json` (stays 2.0, for migration tests).
- `tests/golden/acme_v2.migrated.json` = `convert_20(acme_v2, fixed run)` (state the fixed run in the test).
- New `tests/fixtures/acme.dd.json` (2.1): start from the migrated acme_v2 and add, without changing X1-X8:
  - set entity_class on every entity; E10 stays L3-O with role contractual_obligor (evidence S8);
  - T3 `Acme treasury sleeve`, component LIQUIDITY_SLEEVE, products [P2], with a new issuer entity (role issuer,
    layer null), a sleeve_holding interface from E1 (legal_class OTHER, amount GROSS_FUNDED, currency USD) and a
    reserve_lookthrough interface to a reserve-assets entity (role reserve_assets, layer null; amount basis
    LOOKTHROUGH); one settlement flow edge is optional;
  - amounts on X2 (GROSS_FUNDED) and on one L2_L3 interface (COMMITMENT);
  - an alternative group A1 on two new L2_L3 interfaces of T2 (options a and b) from E1 to E9, so T2 gets two extra
    chain lines with `alt A1a` / `alt A1b`; give one of them an amount with basis GROSS_FUNDED to prove it is not
    counted;
  - an asset_sale interface in T1 from E6 to a new loan_purchaser entity (title_transfer self_reported, amount
    SALE_PROCEEDS);
  - support Z1 CREDIT_ENHANCEMENT for T1 (provider a new protection_provider entity, beneficiary E5) with claims;
  - one third_party_reported claim citing S5;
  - finding U1 scope_unresolved; one gap with material true; scope_note on D1 and D2.
  The document validates against acme.sources.jsonl (extend the ledger fixture only if a new source is unavoidable).
  `dd.py lint` on it returns no warnings.
- v0.5.1 chain strings for T1 must still hold, except that a T1 line now also branches to the asset sale; assert the
  full T1 and T2 line lists exactly (state them in Block A).

### 11.2 Tests
- schema: enums and DOCUMENT additions; skeleton validates structurally; schema_doc matches references/schema.md.
- claims: third_party_reported passes with S5, fails with only first_party or analyst evidence.
- validate: each new rule with one passing and one failing case and exact error text.
- lint: one case per warning kind, incl. `X5: POOL with legal class AP ...` and a within_L2 layer warning.
- framework: flag mapping (six); SEVERITY order; conflicted ignores scope_unresolved; Z subject path; completeness
  only for CORE_CREDIT; chain lines (exact lists for T1, T2, T3: sleeve `(issuer)` and `(reserve)` labels, `alt` tags,
  `(transferee)`); allocation rows and totals (alternative and non-GROSS amounts not counted); five questions on T1
  (exact pairs).
- migrate: acme_v2 -> golden byte-equal; ultimate_obligor -> L3-O cash_flow_source; within_L3 -> L3_L3O; discrepancy
  placeholder; output validates; 1.0 -> 2.1 via migrate_to_current validates.
- runstate: seed from a 2.0 final run (archive, ledger byte copy, migrated doc); finalize refuses the placeholder and
  succeeds after it is replaced; finalize sets skill_version 0.6.0 (assert schema.SKILL_VERSION, not a literal).
- review: golden; section order of section 5.
- render_md: golden; section order of section 6; five-question table; legend lines for the six flags and L3-O.
- flow: suffix letters S/T/I; goldens.
- cli: `dd.py lint` prints the four keys.

## 12. Build and verify (PowerShell, Local)
1. Canary 0.4. `git switch -c v060-curator`.
2. Implement 1-11. Regenerate references/schema.md and goldens with a script under `.scratch/build/`.
3. `python -m pytest -q -rs` -> all pass, no d2 skips.
4. ast check (3.11) over scripts lib tests: OK.
5. Python scans, must find nothing: forbidden symbols (P1 list) in scripts, lib; network imports outside lib/fetch.py
   (AST); `subprocess` outside lib/flow.py; `shell=True`; `os.environ|getenv` in scripts, lib; bytes > 127 and CR in
   scripts lib tests references SKILL.md docs (binary fixtures excluded); any `render_html` reference.
6. Commit with a message file under .scratch\misc\: `feat: curator revisions, schema rwa-dd/2.1 (v0.6.0)`.
   `git show --stat HEAD` lists nothing under handoff_specs/. `git push -u origin v060-curator`;
   `git ls-remote origin v060-curator`.
7. Fresh clone of `v060-curator` into `C:\web3projects\_v060fresh`; `python -m pytest -q -rs`; same counts; delete it.
8. Do NOT deploy. CChat verifies first; the owner deploys after acceptance.
9. Migration smoke with the repo code against copies only: copy `C:\web3projects\rwa-dd-reports\usd-ai`, `huma` and
   `hastra` into `.scratch\build\smoke\`; for each run `python scripts\dd.py init --slug <slug> --url <url> --seed-from
   --root .scratch\build\smoke`, then `validate`, `lint`, `review`; show for each: the init JSON, validate result, the
   lint warning counts per key, and the "Portfolio components", "Framework completeness" and "Scope checks pending"
   sections of the packet. Leave the smoke folder in place for CChat; it is under .scratch (ignored).
10. `git status --porcelain` shows only untracked entries under handoff_specs/.

### 12.1 Done criteria
- [ ] Tests pass in the working copy and the fresh clone; every golden listed and explained.
- [ ] Scans empty; only 0.3 files changed; nothing under handoff_specs/ committed.
- [ ] VERBATIM blocks exact; greps: `curator decision Q1`, `PROTOCOL_ENTITLEMENT`, `scope_unresolved`,
      `Research model (rwa-dd/2.1)`, `rwa-dd/2.1` in references/schema.md, `address, layer, claim and path warnings`.
- [ ] Migration smoke: all three seeded copies validate (lint warnings are expected; report counts).
- [ ] Branch pushed; ls-remote equals HEAD.

## 13. Return contract
- **A** files table (added, changed, deleted, incl. every golden with reason); full lib/migrate.py convert_20 and
  migrate_to_current; the new DOCUMENT parts; new validator and lint rules; framework allocation, five_questions and
  chain-line tables as implemented; the exact asserted chain lines and five-question pairs.
- **B** pytest tails (working copy, fresh clone); ast; scans; smoke outputs per project.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.3: NONE".
- **D** anomalies (Benign / Needs decision / Not covered).

Also write Blocks A-D verbatim, exactly as in your reply, to `handoff_specs/results/handoff-module-v060.result.md`
(UTF-8, LF; overwrite on re-run). Never commit it.
