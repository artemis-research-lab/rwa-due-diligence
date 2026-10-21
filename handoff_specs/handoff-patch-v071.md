# handoff-patch-v071 -- rwa-due-diligence v0.7.1: one counted measure per edge, provenance combinations

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. build the patch in handoff_specs/handoff-patch-v071.md"

## 0. Persistent context
- Base: `main` = `65c8f7d09565a7a9a3c0b45352d860303820d4f2` (v0.7.0 plus spec commit). Target: **SKILL_VERSION
  0.7.1**; **SCHEMA stays rwa-dd/2.2** (no field is added or removed; records in progress stay structurally valid).
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v071-patch` from main, one commit, push it. Do not touch `main`. Do not commit anything under
  `handoff_specs/`. Do NOT deploy.
- D1-D76 apply; this patch adds D77-D79 (section 6).
- Scripts stay OS-neutral Python, standard library only.

### 0.1 Why (round-1 packets of the three 2.2 re-runs, 2026-10-21)
1. Same position counted more than once: hastra X2 (YLDS supplied and HEYLDS receipts), X5 (YLDS, AUTOYLDS and a USD
   figure), usd-ai X2 (PYUSD balance and a USD dashboard figure). Each entry has its own total key, so QA1 passes, but
   the strategy shows two or three "counted" totals for one exposure. A later observation of one position (huma X17)
   cannot be stored without the same effect.
2. Provenance combinations that contradict curator Q8 pass validation: status inferred with origin auditor_procedure
   and assurance TESTED; third_party_reported with TESTED; origin analyst with an assurance value; assurance TESTED
   backed by a non-auditor source; and claims with origin onchain set to TESTED only because v0.7.0 demanded TESTED for
   every verified claim citing an auditor source.
3. Legal-character claims (legal_class, method, security, perfection, title_transfer) verified through an AUP
   procedure: an inspection shows the documents were inspected, not their legal effect (curator Q8 example).
4. The build-time decision of v0.7.0 (Q8 rules apply once origin is set; audits[] exempt) is only in the commit
   message; it needs a decision record.

### 0.2 Verified shared contracts (base commit)
```
lib/framework.py: COUNTABLE; FUNDING_KINDS; _reason(x, amount) -> "alternative A<n><o>" | "not a funding edge" |
  "no amount" | "basis <B> not counted" | "no observation time" | "migrated scope" | "counted";
  allocation(doc) -> Row tuples (strategy, component, interface, entry, kind, value, unit, basis, as_of, scope,
  counted, reason) + .valuation_basis; total_key; allocation_totals; claim_id
lib/claims.py: AUDITED_VERIFIED_ORIGINS = (auditor_procedure, regulator, registry, onchain); AUDIT_SECTIONS =
  ("audits",); q8_exempt(parts); check_claim(): q8 = cites_auditor and origin set and not exempt; verified with q8
  needs assurance TESTED and origin in AUDITED_VERIFIED_ORIGINS; "assurance requires an auditor or independent source"
lib/qa.py: run() -> QA1..QA11 then E:<id>; QA7 three clauses
lib/schema.py: SCHEMA_VERSION "rwa-dd/2.2", SKILL_VERSION "0.7.0", QA_RULES (QA1..QA11), schema_doc()
lib/lint.py: provenance_warnings(doc)
```
If any differs, STOP and report.

### 0.3 File scope (HARD)
```
[EDIT] lib/schema.py (SKILL_VERSION, QA_RULES, schema_doc text), lib/framework.py (allocation reason),
       lib/claims.py, lib/qa.py, lib/lint.py, lib/render_md.py and lib/review.py (only if a reason or rule text is
       rendered from a constant that changes), scripts/dd.py (help text QA1-QA12 only)
[EDIT] references/schema.md (regenerated), references/research-protocol.md (VERBATIM 5.1),
       docs/architecture.md (VERBATIM 5.2, one bullet), docs/decisions.md (section 6)
[EDIT] tests/fixtures/acme.dd.json (only if a new rule rejects it; say what changed), tests/fixtures/acme.qa-expect.json
       (one counted expectation for a second-measure entry), tests/golden/* (regenerated; list every file),
       tests/unit/* as needed
[REUSE -- DO NOT TOUCH] everything else, incl. lib/migrate.py, lib/changes.py, lib/runstate.py, lib/validate.py,
  SKILL.md, handoff_specs/** (except the results file)
```

### 0.4 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-patch-v071.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` =
`65c8f7d09565a7a9a3c0b45352d860303820d4f2`; `git status --porcelain` shows only untracked entries under
`handoff_specs/`; `python --version` >= 3.11; `d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. One counted measure per edge (lib/framework.py, lib/qa.py)
- In `allocation(doc)`, per interface: the first entry (lowest index) whose `_reason` is `counted` keeps it; every
  later entry of the same interface whose `_reason` would be `counted` gets counted false and reason
  `other measure of X<n>[<k>]` (k = index of the counted entry). Entries with any other reason keep it. The rule
  depends only on entry order; no field is added.
- Totals are unchanged in method (only counted rows are summed by total key).
- New `QA12 onemeasure`: no interface has more than one counted allocation row; detail lists interface ids.
  Rule text: `No interface has more than one counted amount (entry 0 or the first countable entry is the position
  measure; later entries are other measures of the same position).` Append to QA_RULES after QA11; expectation
  results follow QA12. Update the dd.py qa help, docstrings and schema_doc to `QA1-QA12`.
- Reader texts: the allocation row reason is shown as is in the review packet and report; no layout change.

## 2. Provenance combinations (lib/claims.py)
Claims under audits[] stay exempt from every rule in this section (q8_exempt). All rules below apply whatever the
status unless stated; error texts exact; existing v0.7.0 rules stay unless replaced here.
- P1 `assurance` non-null requires at least one evidence source with origin auditor (replaces "assurance requires an
  auditor or independent source"): `<path>: assurance requires an auditor source (curator Q8)`.
- P2 origin analyst requires assurance null: `<path>: origin analyst cannot carry assurance`.
- P3 status inferred requires origin analyst or null: `<path>: inferred is the analyst's conclusion; origin must be
  analyst or null`.
- P4 origin auditor_procedure: assurance TESTED requires status verified; assurance NOT_TESTED requires status
  third_party_reported: `<path>: origin auditor_procedure with assurance <A> requires status <S>`.
- P5 verified citing an auditor source with origin set (q8 true) -- replaces the v0.7.0 "verified with an auditor
  source requires assurance TESTED" rule:
  - origin auditor_procedure: assurance TESTED (P4 covers it);
  - origin regulator, registry or onchain: evidence must include a source of that same origin, and assurance must be
    TESTED or NOT_TESTED (what the auditor did for this claim): `<path>: verified with origin <o> needs a <o> source
    in evidence` / `<path>: verified citing an auditor source needs assurance TESTED or NOT_TESTED`;
  - any other origin: `<path>: verified citing an auditor source requires origin auditor_procedure, regulator,
    registry or onchain (curator Q8)`.
  For legal paths, an auditor source counts as a legal verifier only when origin is auditor_procedure and assurance is
  TESTED (unchanged).
- Unchanged: issuer origins only with self_reported or not_found; not_found has null origin and assurance;
  auditor_procedure needs an auditor source; null origin is valid (lint warning, QA7 failure).

## 3. Lint (lib/lint.py)
`provenance_warnings` adds: a claim at interfaces[].legal_class, .method, .security, .perfection or .title_transfer,
or holder_rights[].look_through or .instrument_nature, with status verified and origin auditor_procedure:
`X5.legal_class: an auditor procedure shows the documents were inspected, not their legal effect (curator Q8); take
origin from the source that states the legal character`.

## 4. QA7 (lib/qa.py, QA_RULES text)
QA7 offenders: (a) a claim citing an auditor source (outside audits[]) with status not not_found and origin null;
(b) an issuer origin with status other than self_reported or not_found; (c) any claim that fails P1-P5 (reuse the
claims.py check so QA and validation cannot disagree). Rule text: `No claim citing an auditor source (outside audits[])
has origin null; no claim with an issuer origin has status other than self_reported or not_found; every origin,
assurance and status combination follows the curator Q8 rules.`

## 5. VERBATIM blocks
Each `old` block must be found exactly once; otherwise STOP and report.

### 5.1 references/research-protocol.md
(a) old:
```
- Counting: only CURRENT_BALANCE, POSITION_VALUE and OUTSTANDING_PRINCIPAL amounts on L1_L2 and sleeve_holding edges,
  with an observation time and outside alternative groups, are counted, and totals add only amounts with the same
  basis, unit, valuation basis and observation date. Stocks are never added to flows, commitments or proceeds;
  look-through, alternatives and sale proceeds are never counted. An amount you cannot type is not counted.
```
new:
```
- Counting: only CURRENT_BALANCE, POSITION_VALUE and OUTSTANDING_PRINCIPAL amounts on L1_L2 and sleeve_holding edges,
  with an observation time and outside alternative groups, are counted, and totals add only amounts with the same
  basis, unit, valuation basis and observation date. Stocks are never added to flows, commitments or proceeds;
  look-through, alternatives and sale proceeds are never counted. An amount you cannot type is not counted.
- One edge is one position: only its first countable entry is counted. Put the position measure first (entry 0) and
  add receipt-token quantities, USD values and later observations of the same position after it; start their scope
  with what they are (for example "same position as entry 0, pool receipt units" or "later read of entry 0").
```
(b) old:
```
  Auditor branding never upgrades surrounding claims. Every claim that cites an auditor source sets origin and
  assurance.
```
new:
```
  Auditor branding never upgrades surrounding claims. Every claim that cites an auditor source sets origin and
  assurance. Combinations: inferred is your conclusion (origin analyst or null, no assurance); auditor_procedure with
  TESTED is verified, with NOT_TESTED third_party_reported; a claim verified by a regulator, registry or on-chain
  source keeps that origin and states in assurance whether a cited auditor also tested it; assurance always needs an
  auditor source. An AUP or attestation never establishes legal character (legal class, method, security,
  perfection, title, look-through, instrument nature): take that origin from the document or filing that states it.
```

### 5.2 docs/architecture.md
old:
```
- Counting: only stock amounts (balances, position values, outstanding principal) on funding edges, with an
  observation time and outside alternative paths, are summed, and only within the same basis, unit and date.
```
new:
```
- Counting: only stock amounts (balances, position values, outstanding principal) on funding edges, with an
  observation time and outside alternative paths, are summed, one measure per edge, and only within the same basis,
  unit and date.
```

## 6. Decisions (append to docs/decisions.md, after D76, before "## Validation records")
```
- D77 - Q8 gating - 2026-10-21 - The curator Q8 auditor-source rules apply once a claim's origin is set; a null origin is valid but fails QA7, so finalize refuses; claims under audits[] describe the audit itself and are exempt (decided during the v0.7.0 build).
- D78 - One measure per edge - 2026-10-21 - Only the first countable amount of an interface is counted; later entries are other measures of the same position (QA12).
- D79 - Provenance combinations - 2026-10-21 - Assurance needs an auditor source; inferred has origin analyst or null; auditor_procedure TESTED is verified and NOT_TESTED third_party_reported; a regulator, registry or on-chain verification keeps that origin; AUP procedures never establish legal character (lint).
```
Validation records, append:
`- 2026-10-21 - Round-1 packets of the 2.2 re-runs (hastra, usd-ai, huma): double-counted measures and Q8 combinations found; fixed in v0.7.1.`

## 7. Tests (offline)
- framework: an interface with entries [CURRENT_BALANCE YLDS, CURRENT_BALANCE HEYLDS, POSITION_VALUE USD] (all with
  as_of) gives counted [True, False, False] with reasons `counted`, `other measure of X2[0]`, `other measure of X2[0]`;
  an interface whose entry 0 is CUMULATIVE_FUNDED and entry 1 CURRENT_BALANCE counts entry 1; totals contain one
  key for that interface.
- qa: QA12 passes on the fixture and fails on a copy with the counting rule monkeypatched off; QA7 (c) fails on a
  P4-violating claim; results list QA1..QA12 then E:<id>.
- claims: P1-P5 each one passing and one failing case with exact text; audits[] claim with NOT_APPLICABLE and an
  independent non-auditor source passes; onchain-origin verified claim citing an onchain and an auditor source passes
  with NOT_TESTED and fails with null assurance.
- lint: legal-character warning on X<n>.legal_class verified with auditor_procedure; none for origin regulator.
- schema: schema_doc matches references/schema.md; QA_RULES has 12 entries.
- Golden reports/packets regenerated only where reason or rule texts changed; list every file.
- Version assertions use schema.SKILL_VERSION.

## 8. Build and verify (PowerShell, Local)
1. Canary 0.4. `git switch -c v071-patch`.
2. Implement 1-7; regenerate references/schema.md and goldens with a script under `.scratch/build/`.
3. `python -m pytest -q -rs` -> all pass, no d2 skips. ast check (3.11) OK. Scans as in v0.7.0 step 5: empty.
4. Commit (message file under .scratch\misc\): `fix: one counted measure per edge, Q8 provenance combinations
   (v0.7.1)`. `git show --stat HEAD` lists nothing under handoff_specs/. `git push -u origin v071-patch`;
   `git ls-remote origin v071-patch`.
5. Fresh clone into `C:\web3projects\_v071fresh`; pytest; same counts; delete it.
6. In-progress smoke, read-only on copies: copy `C:\web3projects\rwa-dd-reports\usd-ai`, `huma`, `hastra` into
   `.scratch\build\smoke071\` (delete it first if present) and, for each, run with the repo code `validate`, `lint`
   and `qa` on the copied working run (no init, no directives, no finalize). Report per project: validate error
   count and the first 10 errors, lint counts per key, qa failed list, and the allocation rows whose reason starts
   with `other measure of`. Errors are expected where round-2 work has not yet fixed the claims; do not edit the
   copies. Leave the folder in place.
7. Do NOT deploy. `git status --porcelain` shows only untracked entries under handoff_specs/.

## 9. Return contract
- **A** files table (incl. every golden with reason); the new allocation code path; P1-P5 as implemented with error
  texts; QA7 and QA12 code; lint addition; fixture changes if any.
- **B** pytest tails (working copy, fresh clone); ast; scans; smoke outputs per project.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.3: NONE".
- **D** anomalies (Benign / Needs decision / Not covered).

Also write Blocks A-D verbatim, exactly as in your reply, to `handoff_specs/results/handoff-patch-v071.result.md`
(UTF-8, LF; overwrite on re-run). Never commit it.
