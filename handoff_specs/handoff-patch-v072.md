# handoff-patch-v072 -- rwa-due-diligence v0.7.2: v2.2 acceptance closure (AC-01, AC-03, AC-04)

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. build the patch in handoff_specs/handoff-patch-v072.md"

## 0. Persistent context
- Base: `main` = `64c34da533250228bca728a431a70a63dad6816e` (v0.7.1 plus spec commit). Target: **SKILL_VERSION
  0.7.2**; **SCHEMA stays rwa-dd/2.2** (no field added, removed or renamed; v2.2 records stay structurally valid).
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v072-closure` from main, one commit, push it. Do not touch `main`. Do not commit anything under
  `handoff_specs/`. Do NOT deploy.
- D1-D79 apply; this patch adds D80-D83 (section 7).
- Scripts stay OS-neutral Python, standard library only. Read-only skill: no network code outside lib/fetch.py.
- The accepted v2.2 design is preserved (curator closure request, section 2): this patch changes no classification
  rule, no enum and no counting rule other than the time-basis condition in 2.

### 0.1 Why (curator closure request, 2026-10-21)
- AC-01: expectation results reported `@U9` without naming the finding actually tested (v2.2 R1, carried from v2.1
  U9) while a different current U9 exists (carried from D1). Every result must name its canonical target and the
  legacy mapping; an id migration must never redirect a test silently.
- AC-03: an amount's `as_of` was filled with the time a web page was viewed. The curator distinguishes observed_at
  (when the system accessed the source), data_as_of (when the value applies, only where the source establishes it) and
  block_timestamp (verified block time). Aggregation must never use access time as data time.
- AC-04: a complete per-sample package with a manifest (file names, run ids, SHA-256) that reproduces the reported
  validation and regression results.

### 0.2 Verified shared contracts (base commit)
```
lib/schema.py: SCHEMA_VERSION "rwa-dd/2.2", SKILL_VERSION "0.7.1"; AMOUNT (basis, value, unit, as_of
  DateOrTimestamp nullable, block, chain, scope, valuation_basis); SOURCE.retrieved_at Timestamp nullable;
  EXPECT_KEYS, EXPECT_OPS; QA_RULES QA1..QA12; schema_doc()
lib/framework.py: class Row(tuple); _reason() incl. "no observation time"; allocation(); resolve(doc, path);
  RESOLVE_PATTERN; claim_id()
lib/qa.py: run(); _entry_errors(i, entry) (keys must equal EXPECT_KEYS); parse_expectations(); check_expectation()
  -> {"id", "rule", "result", "detail"}
lib/runstate.py: RENDERERS; ProjectDir.outputs() = dd.json, derived.json, renderers, flows; finalize() writes
  derived.json via render_md.derived()
lib/render_md.py: derived(); Appendix N expectation table
```
If any differs, STOP and report.

### 0.3 File scope (HARD)
```
[EDIT] lib/schema.py, lib/framework.py, lib/qa.py, lib/validate.py, lib/lint.py, lib/runstate.py, lib/review.py,
       lib/render_md.py, lib/flow.py (only a d2-version helper if none exists), scripts/dd.py
[NEW]  lib/package.py
[EDIT] references/schema.md (regenerated), references/research-protocol.md (VERBATIM 6.1), SKILL.md (VERBATIM 6.2),
       docs/architecture.md (VERBATIM 6.3), docs/decisions.md (section 7)
[EDIT] tests/fixtures/acme.dd.json (only where a new rule rejects it; say what), tests/fixtures/acme.qa-expect.json,
       tests/golden/* (regenerated; list every file), tests/unit/* as needed (new: test_package.py)
[REUSE -- DO NOT TOUCH] lib/migrate.py, lib/changes.py, lib/claims.py, lib/fetch.py, lib/pdftext.py, lib/ledger.py,
  lib/directives.py, assets/**, tools/**, CLAUDE.md, .gitattributes, pytest.ini, .gitignore, handoff_specs/** (except
  the results file)
```

### 0.4 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-patch-v072.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` =
`64c34da533250228bca728a431a70a63dad6816e`; `git status --porcelain` shows only untracked entries under
`handoff_specs/`; `python --version` >= 3.11; `d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. Canonical targets in expectation results (AC-01; lib/qa.py, lib/framework.py, lib/schema.py)
- `EXPECT_KEYS` gains an optional key `target`: an entry has exactly the five v0.7.0 keys, or those plus `target`
  (a string matching `^(E|P|T|X|Z|G|D|C|U|R)[1-9][0-9]*$`). An entry whose path starts with `@` without `target` is
  malformed: `expectations[<i>].target: required for a legacy (@) path` (ContractError, exit 3).
- `framework.resolve_target(doc, path)` -> `(canonical_id, legacy_id or None)`: canonical_id is the id of the object
  the path's head resolves to (for `@<id>` the finding found through carried_from; for `P<n>.holder_rights` the
  product id), legacy_id is `<id>` for `@<id>` paths. Raises KeyError as resolve does.
- Every expectation result gains keys `target` (canonical id or null when unresolved), `legacy` (legacy id or null)
  and `mapping` (text, "" when none):
  - `@U9` resolving to R1: mapping `legacy U9 -> R1 (carried_from U9)`; when another current finding has id U9,
    append `; current U9 is a different finding (carried_from D1)`.
  - a plain finding path whose finding has carried_from different from its id: mapping `U9 carried_from D1`.
  - non-finding targets: mapping "".
- When the entry has `target` and the canonical id differs: result fail, detail `target mismatch: expected R1, resolved
  <id>` (this is the guard against silent redirection).
- `detail` keeps its v0.7.0 form but begins with `<canonical id>: ` (e.g. `R1: @U9.type in [...] -> ...`).
- Results of QA1..QA13 get `target`, `legacy`, `mapping` null/null/"" so every result object has the same keys.
- Review packet QA table and report Appendix N expectation rows add columns `target` and `mapping`.

## 2. Amount time basis (AC-03; lib/validate.py, lib/framework.py, lib/qa.py, lib/render_md.py, lib/review.py)
Definitions (no field is renamed; schema_doc and the legend state them):
- `amounts[].as_of` is **data_as_of**: the date or time the value applies, as established by the source (a statement
  or report date, an API `updatedAt`, or the block time of an on-chain read). Null when the source does not establish
  it. It is never the time a page was opened.
- **observed_at** is derived: the latest `retrieved_at` among the sources cited in the amount's value evidence
  (null when none has one).
- **block_timestamp**: when `block` is set, `as_of` is that block's time and must be a full timestamp.
Rules:
- validate: `block` non-null requires `as_of` to be a full timestamp:
  `<path>.as_of: a block read needs the block timestamp (curator AC-03)`.
- validate: `block` null and `as_of` equal (same string, or same instant when both are timestamps) to the
  `retrieved_at` of any cited value source:
  `<path>.as_of: equals the retrieval time of <S id>; record the time the source gives for the value, or null (curator AC-03)`.
- framework: Row gains `observed_at` and `time_basis` (attributes like valuation_basis, tuple equality unchanged):
  `block` (block set), `source` (as_of set, no block), `unresolved` (as_of null). The `_reason` text
  `no observation time` becomes `data time not established`.
- QA13 `timebasis`: no counted amount has time_basis unresolved, and no amount without a block has as_of equal to the
  retrieval time of a cited source. Rule text: `No counted amount lacks an established data time, and no data time is
  a source retrieval time (curator AC-03).`
- Review "Amounts" table and report amount tables add `data as of`, `time basis` and `observed at` columns; the amount
  cell becomes `<value> <unit> <BASIS> data <as_of or not established> (<time basis>) [FLAG] (sources)`.
- Report metadata `Data observed` becomes `Data as of` (earliest and latest non-null as_of) and gains `Sources
  retrieved` (earliest and latest retrieved_at among cited amount sources).
- derived.json allocation rows add `observed_at` and `time_basis`.

## 3. Package manifest and verification (AC-04; lib/package.py, lib/runstate.py, scripts/dd.py)
- `package.manifest(project, state, doc)` -> dict written by finalize (after derived.json) as `<slug>.manifest.json`
  in the project directory and added to `ProjectDir.outputs()` (amend archives it with the rest):
```
{"manifest_version": "rwa-dd-manifest/1", "slug", "run_id", "seeded_from", "schema_version", "skill_version",
 "finalized_at", "rounds", "execution": {"python": "<major.minor.micro>", "platform": "<platform.system()>",
   "d2": "<d2 --version output or n/d>"},
 "files": [{"path": "<relative to the project dir, forward slashes>", "role": "<role>", "bytes": n,
            "sha256": "<hex>"}, ...],
 "checks": {"validate_errors": 0, "lint_warnings": 0, "qa_failed": [], "record_sha256_match": true}}
```
  files (sorted by path): `<slug>.dd.json` (record), `<slug>.derived.json` (derived), `<slug>.report.md` (report),
  every `<slug>.flow-*.svg` (diagram), `audit/sources.jsonl` (ledger), `audit/qa-expect.json` (expectations, when
  present), `audit/state.json` (run_state), every `audit/rounds/r<k>/*` file (round_record), every directive and
  amendment log of this run under `.scratch/logs/<run_id>-*` (analyst_input). The manifest never lists itself.
- `dd.py verify --slug <s> --root .` (read-only): recomputes every listed SHA-256 and byte count, re-validates the
  record against the ledger, re-runs lint and QA (with the listed expectations), compares the recomputed QA results
  (id, result, target) with derived.json, and checks record_sha256. Prints `{"result": "PASS"|"FAIL", "failures":
  [...]}`; exit 0 on PASS, 6 on FAIL (new code; document in SKILL.md 6.2 and dd.py help). It writes nothing.
- d2 version: reuse the existing version check in lib/flow.py if one exists; otherwise add a helper there returning
  the first line of `d2 --version` (the only subprocess stays in lib/flow.py).

## 4. Expectation fixture and protocol
- `tests/fixtures/acme.qa-expect.json`: add `target` to every `@` entry; add one plain-id entry on a carried-over
  finding; add one entry with a deliberately wrong `target` in a test-local copy (not the fixture) to prove the
  mismatch fail.
- Fixture amounts: if the new AC-03 rules reject a fixture amount, fix the fixture (say what changed).

## 5. Tests (offline)
- qa: `@` path without target -> exit 3 text; target mismatch -> fail with detail; mapping texts for `@` with and
  without a reused current id, and for a plain path with carried_from; result key set identical for QA and E rows;
  QA13 pass and fail (counted amount with null as_of cannot exist, so test the retrieval-time clause and a monkeypatched
  counting rule).
- validate: block without full timestamp; as_of equal to a cited source's retrieved_at (string and instant forms);
  a block read whose as_of equals retrieved_at passes.
- framework: time_basis per row; observed_at = latest retrieved_at; reason text.
- package: manifest file list and roles for a finalized tmp run (incl. a seeded run with logs); verify PASS on it;
  verify FAIL after changing one byte of the report, of the ledger and of derived.json (each separately).
- runstate: finalize writes manifest.json last; amend archives it; outputs list includes it.
- render_md / review goldens regenerated; Appendix N columns; metadata rows.
- schema: QA_RULES 13 entries; EXPECT_KEYS doc; schema_doc matches references/schema.md.

## 6. VERBATIM blocks (each old block must be found exactly once; otherwise STOP)

### 6.1 references/research-protocol.md
old:
```
- interfaces[].as_of is the date the legal terms were observed; amounts carry their own observation times.
```
new:
```
- interfaces[].as_of is the date the legal terms were observed. An amount's as_of is the time the value applies as
  the source establishes it (statement or report date, API updatedAt, block time); never the time you opened the
  page. An undated web figure keeps as_of null: it is shown, not counted. For an on-chain read set block and chain and
  use the block time. Retrieval times live in the source ledger and are shown as observed-at (curator AC-03).
```

### 6.2 SKILL.md
old:
```
   (exit 5 lists failed checks). In a run seeded from an earlier schema, re-check every carried-over amount (basis,
```
new:
```
   (exit 5 lists failed checks; `dd.py verify` exit 6 after finalize means the package does not reproduce). In a run
   seeded from an earlier schema, re-check every carried-over amount (basis,
```
If the old line differs only in spacing, report the actual line in Block D and replace that line.

### 6.3 docs/architecture.md
old:
```
- Counting: only stock amounts (balances, position values, outstanding principal) on funding edges, with an
  observation time and outside alternative paths, are summed, one measure per edge, and only within the same basis,
  unit and date.
```
new:
```
- Counting: only stock amounts (balances, position values, outstanding principal) on funding edges, with a data time
  established by the source or the block, outside alternative paths, are summed, one measure per edge, and only within
  the same basis, unit and date. Retrieval times are observed-at metadata, never data times.
- Package: finalize writes a manifest of every output, ledger, expectation, round record and analyst input with
  SHA-256 and execution metadata; `dd.py verify` reproduces the checks from the package.
```

## 7. Decisions (append after D79, before "## Validation records")
```
- D80 - Canonical test targets - 2026-10-21 - Every expectation result names its canonical target and any legacy mapping; a legacy (@) path must declare its target, and a mismatch fails (curator AC-01).
- D81 - Amount time basis - 2026-10-21 - An amount's as_of is the data time the source or block establishes; retrieval time is derived observed-at metadata; undated figures are shown, not counted; QA13 (curator AC-03).
- D82 - Package manifest - 2026-10-21 - Finalize writes <slug>.manifest.json (files, roles, SHA-256, run and execution metadata); dd.py verify reproduces the checks read-only (curator AC-04).
- D83 - Schema unchanged - 2026-10-21 - v0.7.2 closes the curator's v2.2 acceptance tasks without changing schema rwa-dd/2.2 or the accepted classification rules.
```
Validation records, append:
`- 2026-10-21 - Curator v2.2 review: design accepted, closure tasks AC-01 to AC-04 requested; tooling in v0.7.2.`

## 8. Build and verify (PowerShell, Local)
1. Canary 0.4. `git switch -c v072-closure`.
2. Implement 1-7; regenerate references/schema.md and goldens with a script under `.scratch/build/`.
3. `python -m pytest -q -rs` -> all pass, no d2 skips. ast (3.11) OK. Scans as in v0.7.0 step 5 plus: `subprocess`
   only in lib/flow.py; no write in lib/package.py outside the project directory helpers.
4. Commit (message file under .scratch\misc\): `feat: v2.2 closure - canonical test targets, amount time basis,
   package manifest (v0.7.2)`. Nothing under handoff_specs/. `git push -u origin v072-closure`; ls-remote.
5. Fresh clone into `C:\web3projects\_v072fresh`; pytest; same counts; delete it.
6. Smoke on copies (read-only on the originals): copy `C:\web3projects\rwa-dd-reports\usd-ai`, `huma`, `hastra` into
   `.scratch\build\smoke072\` (delete first if present). For each, with the repo code on the copy: `validate` on the
   final record (report the AC-03 errors; they are expected for hastra X2/X5/X7 entries that carry a page view time),
   `qa` with the copied expectations (report failures; `@` entries without target are expected to be malformed until
   the analyst supplies new expectation files). Do not amend, finalize or edit the copies. Leave the folder in place.
7. Do NOT deploy. `git status --porcelain` shows only untracked entries under handoff_specs/.

## 9. Return contract
- **A** files table (incl. every golden with reason); resolve_target and the result-building code; the two new
  validate rules and QA13 with texts; Row attributes; package.manifest and verify code; fixture changes.
- **B** pytest tails (working copy, fresh clone); ast; scans; smoke outputs per project.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.3: NONE".
- **D** anomalies (Benign / Needs decision / Not covered).

Also write Blocks A-D verbatim, exactly as in your reply, to `handoff_specs/results/handoff-patch-v072.result.md`
(UTF-8, LF; overwrite on re-run). Never commit it.
