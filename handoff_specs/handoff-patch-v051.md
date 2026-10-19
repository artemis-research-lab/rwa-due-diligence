# handoff-patch-v051 -- rwa-due-diligence v0.5.1: chain lines, subject paths, interface checks, report columns

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. apply the patch in handoff_specs/handoff-patch-v051.md"

## 0. Persistent context
- Read `docs/architecture.md` before executing. Module names below match it.
- Base: `main` = `284cde37ad8dabc9157bd08289e7b5dc7edf3327` (v0.5.0 plus spec commit). Target: **SKILL_VERSION 0.5.1**, schema stays **rwa-dd/2.0** (no field added or removed).
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v051-patch` from main, one commit, push it. Do not touch `main`. Do not commit anything under `handoff_specs/`.
- D1-D46 apply; this patch adds D47-D51 (section 8).
- Scripts stay OS-neutral Python, standard library only.

### 0.1 Why
Three seeded runs (usd-ai, huma, hastra, 2026-10-19/20) re-mapped onto the three-layer model exposed renderer and validator gaps that would mislead the risk curator in the sample reports:
1. Chain lines stop at within-layer hops (hastra: holders -> vault -> pool, then the pool's trust and Figure Lending start separate lines) and never reach the L3 ultimate obligors the analyst now records (L3-O).
2. Layer labels in chain lines use an entity's first function, so an entity acting as L1 and L2 is always shown as L1.
3. The discrepancy subject pattern rejects field names with digits (`l3_business`), so gaps and discrepancies on L3 business fields cannot name their subject.
4. Holder-rights claims have no subject path (holder_rights entries have no id), so `P<n>.holder_rights.<field>` subjects pass validation but never make a claim CONFLICTING.
5. An interface whose `from` equals its `to` validates (huma had two such self-loops).
6. Report sections 5 and 6 omit `counterparty`, a mandatory framework edge field.
The owner also adopted a return-contract file (workflow patch rev6, J.1b): CC writes Blocks A-D to `handoff_specs/results/`.

### 0.2 Verified shared contracts (base commit)
```
lib/schema.py: SUBJECT_PATTERN = r"^(E|P|T|X)[1-9][0-9]*(\.[a-z_]+){0,3}$" (line 82); findings[].subjects uses it;
  SKILL_VERSION "0.5.0"; schema_doc() documents the subject pattern
lib/framework.py: subject_path(parts, doc); conflicted(doc); flag(); flags(doc); worst(); completeness(doc);
  CHAIN_ORDER = ("holder_L1", "L1_L2", "L2_L3"); _code(); _hop(x); _entity_label(doc, eid, strategy_id); _paths();
  chain_line(doc, strategy_id) -> list of str
lib/validate.py: _framework_errors(doc, ids, errors) holds the interface rules (holder_L1 / product-id rules,
  route/method kind rules)
lib/render_md.py: _l1_l2(doc, cell) columns id|strategy|from -> to|route|legal class|instrument|claim holder|terms|
  governing law; _l2_l3(doc, cell) columns id|strategy|from -> to|method|legal class|security|collateral|perfection|
  enforcement|recourse|terms
lib/review.py: chain_lines(doc) calls framework.chain_line
tests/fixtures/acme.dd.json: E1 functions (L1 token_issuer null, L1 holder_counterparty null, L2 lender_of_record T2);
  E7 (L3 financing_recipient T1, L3 ultimate_obligor T1); interfaces X1-X7 (X3 within_L2 E5->E6 legal_class DI;
  X7 T2 L2_L3 E1->E9); 8 sources
tests/unit/test_framework.py: test_chain_lines_on_fixture, test_chain_line_follows_connected_interfaces,
  test_chain_line_unknown_layer_and_empty
.gitignore: .venv/ dist/ __pycache__/ *.pyc .env .pytest_cache/ /.scratch/ /.pytest_tmp/
```

### 0.3 File scope (HARD)
```
[EDIT] lib/framework.py         chain_line rewrite (section 1), holder-rights subject paths (section 2)
[EDIT] lib/schema.py            SUBJECT_PATTERN (section 3); SKILL_VERSION "0.5.1"; schema_doc text if it quotes the pattern
[EDIT] lib/validate.py          from != to rule (section 4)
[EDIT] lib/render_md.py         counterparty column (section 5); Appendix C legend line (section 5)
[EDIT] references/schema.md     regenerated
[EDIT] references/research-protocol.md   VERBATIM replacement 6.1
[EDIT] .gitignore               add one line (section 6.2)
[EDIT] docs/decisions.md        section 8
[EDIT] tests/fixtures/acme.dd.json   additions in section 7 only
[EDIT] tests/golden/*           regenerated; list every changed file in Block A
[EDIT] tests/unit/test_framework.py, test_validate.py, test_schema.py, test_render_md.py, test_review.py, and any
       other test whose expected values change because of the fixture additions
[REUSE -- DO NOT TOUCH] everything else, incl. lib/review.py, lib/flow.py, lib/runstate.py, lib/migrate.py,
  scripts/dd.py, SKILL.md, docs/architecture.md, assets/**, tools/**, handoff_specs/**
```
`lib/review.py` needs no edit: it calls `framework.chain_line`.

### 0.4 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-patch-v051.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` =
`284cde37ad8dabc9157bd08289e7b5dc7edf3327`; `git status --porcelain` shows only untracked entries under
`handoff_specs/`; `python --version` >= 3.11; `d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. Chain lines (lib/framework.py)

Replace `chain_line` (and its helpers as needed) with this behaviour. Output stays a list of ASCII strings, one per path.

**Positions.** Each node on a path has a position: holder_L1 leads to L1; L1_L2 to L2; L2_L3 to L3; within_Lk keeps Lk.

**Continuations.** From a node at position Lk, the path continues along interfaces of the same strategy whose `from`
is that node, in interface-id order, when the interface kind is:
- `within_Lk`;
- the forward kind of Lk (`L1_L2` at L1, `L2_L3` at L2; none at L3);
- at L1 only: `L2_L3`, when the node's entity has an L2 function whose strategy is this strategy or null. The node's
  label then reads `(L1/L2)` and the next node is at L3.
A node already on the current path is never entered again (cycle guard). Every maximal path is one line; a node with
several continuations branches into several lines, in interface-id order (depth first).

**Starts.** Lines start at each `holder_L1` interface of the strategy, in id order. Afterwards, every `L1_L2` or
`L2_L3` interface of the strategy that no line has used starts a line of its own (its `from` node gets the position
implied by the kind: L1 for L1_L2, L2 for L2_L3), in id order; such lines continue by the same rules. `within_*`
interfaces never start a line.

**Hop codes.** holder_L1 `[legal_class]`; L1_L2 `[route; legal_class]`; L2_L3 `[method; security]`; within_*
`[legal_class]`. Values via the existing `_code` (`?` for null, `+` joins lists).

**Node labels.** `<E id> <legal_name value>` (id alone when null), then the position in parentheses. A node reached
through a `within_L3` interface whose entity has a function with role `ultimate_obligor` and strategy this strategy
or null is labelled `(L3-O)`. Entity not found: id alone with `(?)` as today. Products as today: `P<n> holders`.

**Expected on the fixture after section 7:**
```
T1:
P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E5 Acme Credit Fund LP (L2) -> [DI] -> E6 Acme Warehouse SPV Ltd (L2) -> [DL; secured] -> E7 Example Equipment Lessors Ltd (L3) -> [OTHER] -> E10 (L3-O)
P1 holders -> [DI] -> E1 Acme Yield Issuer Ltd (L1) -> [FUND; FI] -> E5 Acme Credit Fund LP (L2) -> [DI] -> E6 Acme Warehouse SPV Ltd (L2) -> [AP; ?] -> E8 Example Receivables Originator (L3)
T2:
P2 holders -> [OTHER] -> E1 Acme Yield Issuer Ltd (L1/L2) -> [PT; unsecured] -> E9 (L3)
```
Assert these exact strings. If a fixture value differs from what this spec assumes (names, codes), stop and report
in Block D rather than editing the fixture to match.

Keep `CHAIN_ORDER` only if still used; `completeness` is unchanged.

## 2. Holder-rights subject paths (lib/framework.py)

`subject_path(parts, doc)`: when `parts[0] == "holder_rights"`, return
`"<product id>.holder_rights.<field names below the entry joined by '.'>"`, where the product id is
`doc["holder_rights"][parts[1]]["product"]` (indexes dropped as today). Example: `P1.holder_rights.look_through`.
`conflicted` and `flags` then work unchanged. All other paths are unchanged.

## 3. Subject pattern (lib/schema.py)

`SUBJECT_PATTERN = r"^(E|P|T|X)[1-9][0-9]*(\.[a-z][a-z0-9_]*){0,3}$"`. Field names must start with a letter; digits
allowed after. Update the human description and `schema_doc` text if they quote the pattern; regenerate
`references/schema.md`.

## 4. Validation (lib/validate.py)

In `_framework_errors`, for each interface: when `x["from"] == x["to"]`, append
`"interfaces[%d]: from and to must differ (%s)" % (i, x["from"])`.

## 5. Report (lib/render_md.py)

- `_l1_l2`: insert column `counterparty` (cell of `x["counterparty"]`) right after `legal class`.
- `_l2_l3`: insert column `counterparty` right after `legal class`.
- Appendix C legend: add one line after the Layers line:
  `- L3-O: the L3 business's paying customers or end borrowers (ultimate obligors), recorded as layer L3 with role ultimate_obligor and linked by within_L3 interfaces.`
Nothing else in the report changes.

## 6. Documents

### 6.1 references/research-protocol.md (VERBATIM replacement)
Replace exactly:
```
  PARTIALLY_VERIFIED; not_found UNRESOLVED; any claim named by a discrepancy finding's subjects CONFLICTING. Name the
  subjects (for example `X3.security`, `T1.default_path.loss_waterfall`) on every discrepancy.
```
with:
```
  PARTIALLY_VERIFIED; not_found UNRESOLVED; any claim named by a discrepancy finding's subjects CONFLICTING. Name the
  subjects (for example `X3.security`, `T1.default_path.loss_waterfall`, `T2.l3_business.performance`,
  `P1.holder_rights.look_through`) on every discrepancy. Never point an interface at its own source entity.
```
If the original text is not found exactly once, STOP and report.

### 6.2 .gitignore
Append the line `/handoff_specs/results/`.

## 7. Fixture additions (tests/fixtures/acme.dd.json)
- Entity **E10**: legal_name, jurisdiction, entity_type, registration_id, license_status all not_found with empty
  evidence; licenses []; functions `[{"layer": "L3", "role": "ultimate_obligor", "strategy": "T1", "evidence": ["S8"]}]`.
- Interface **X8**: strategy T1, kind `within_L3`, from E7, to E10; legal_class `{"value": "OTHER", "status":
  "self_reported", "evidence": ["S8"], "subject": null, "note": "Equipment leases between the lessor and its lessees."}`
  (match the fixture's existing claim shape, including any other claim keys); every other claim not_found with empty
  evidence; as_of null.
- No other fixture change. The document must still validate against acme.sources.jsonl.

## 8. Decisions (append to docs/decisions.md)
```
- D47 - Chain lines - 2026-10-20 - Chain lines follow within-layer hops and continue to L3 ultimate obligors (L3-O); node labels show the position on the path.
- D48 - L3-O - 2026-10-20 - Ultimate obligors stay layer L3 with role ultimate_obligor and are linked by within_L3 interfaces; a separate schema layer waits for curator feedback.
- D49 - Holder-rights subjects - 2026-10-20 - Holder-rights claims have the subject path P<n>.holder_rights.<field>, so discrepancies can flag them CONFLICTING.
- D50 - Subject field names - 2026-10-20 - Subject field names may contain digits after the first letter.
- D51 - No self-loops - 2026-10-20 - An interface's from and to must differ.
```
Validation records, append:
`- 2026-10-20 - Seeded re-maps of usd-ai, huma and hastra (rwa-dd/2.0): layer convention L1 vault and legal entity, L2 credit provider, L3 borrower running the business, L3-O its paying customers; renderer and validator gaps fixed in v0.5.1.`

`docs/architecture.md`: no change (no functional boundary, Known Limit or invariant changed); say so in Block A.

## 9. Tests (offline)
- framework: the three exact T1/T2 lines of section 1; a branch test (a node with two continuations yields two lines
  in id order); a cycle test (two interfaces E_a->E_b and E_b->E_a within one layer terminate); an L1/L2 test (the T2
  line); an orphan-start test (an L2_L3 interface unreachable from holders starts its own line); within_* never starts
  a line; holder-rights subject path `P1.holder_rights.look_through` (and that a discrepancy naming it makes that
  claim CONFLICTING while the same field of P2 stays unaffected).
- schema: pattern accepts `T1.l3_business.performance`, `P1.holder_rights.look_through`; rejects `T1.3x`,
  `T1.Field`, `X1.a.b.c.d`.
- validate: from == to gives the exact error text; the fixture still validates.
- render_md: sections 5 and 6 headers include `counterparty` after `legal class`; legend contains the L3-O line.
- Regenerate goldens (acme.report.md, acme.review.md, any acme.flow-* that changes); list each in Block A with a
  one-line reason.

## 10. Build and verify (PowerShell, Local)
1. Canary 0.4. `git switch -c v051-patch`.
2. Implement sections 1-8. Regenerate references/schema.md and goldens with a script under `.scratch/build/`.
3. `python -m pytest -q -rs` -> all pass, no d2 skips.
4. ast check (3.11) over scripts lib tests: OK.
5. Python scans, must find nothing: forbidden symbols (P1 list) in scripts, lib; network imports outside
   lib/fetch.py (AST); `subprocess` outside lib/flow.py; `shell=True`; `os.environ|getenv` in scripts, lib; bytes
   > 127 and CR bytes in scripts lib tests references SKILL.md docs (binary fixtures excluded).
6. Commit with a message file under .scratch\misc\: `fix: chain lines to L3-O, subject paths, no self-loops (v0.5.1)`.
   `git show --stat HEAD` lists nothing under handoff_specs/. `git push -u origin v051-patch`;
   `git ls-remote origin v051-patch`.
7. Fresh clone of `v051-patch` into `C:\web3projects\_v051fresh`; `python -m pytest -q -rs`; same counts; delete it.
8. Install with `tools\deploy.ps1 -ClaudeCode` only if no DD session is running a command right now (sessions waiting
   for directives are fine); show SHIP/DENIED lines.
9. Read-only smoke from the installed copy, against copies only: copy `C:\web3projects\rwa-dd-reports\huma` and
   `...\hastra` to `.scratch\build\smoke\`; for each run `dd.py validate`, `dd.py review` (writes into the copy only)
   and show the "Three-layer chains" section of the new packet. Delete the smoke folder afterwards.
10. `git status --porcelain` shows only untracked entries under handoff_specs/ (results/ is now ignored).

### 10.1 Done criteria
- [ ] Tests pass in the working copy and the fresh clone; goldens listed and explained.
- [ ] Scans empty; only 0.3 files changed; nothing under handoff_specs/ committed.
- [ ] Exact chain strings of section 1 asserted; smoke shows hastra T1/T2 chains unbroken from holders to L3-O.
- [ ] Branch pushed; ls-remote equals HEAD.

## 11. Return contract
- **A** files table (changed files, every golden with reason; architecture.md unchanged and why); full new
  `chain_line` and `subject_path`; the new validator rule.
- **B** pytest tails (working copy, fresh clone); ast; scans; deploy lines; smoke chain sections for huma and hastra.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.3: NONE".
- **D** anomalies (Benign / Needs decision / Not covered).

Also write Blocks A-D verbatim, exactly as in your reply, to `handoff_specs/results/handoff-patch-v051.result.md`
(UTF-8, LF; create the folder; overwrite on re-run). Never commit it.
