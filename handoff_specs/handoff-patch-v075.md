# handoff-patch-v075 -- rwa-due-diligence v0.7.5: amendment change log by id, full amendment history

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. build the patch in handoff_specs/handoff-patch-v075.md"

## 0. Persistent context
- Base: `main` = `45318b7409ea43b7701f360d3a607510e28a06e4` (v0.7.4 + D90 + spec commit). Target: **SKILL_VERSION
  0.7.5**; schema stays rwa-dd/2.2. D1-D90 apply; this patch adds D91.
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v075-amendlog` from main, one commit, push it. Do not touch `main`. Do not commit anything under
  `handoff_specs/`. Do NOT deploy.

### 0.1 Why
The AC-05 finals carry `amendment_changes` rows that did not happen. `changes.diff` pairs findings through
`carried_from`, which is right against the seeded earlier-schema record (ids were re-assigned) but wrong between two
final versions of the same run, where ids are stable and `carried_from` still names v2.1 ids. Example (huma,
amendment 3): rows `D1 -> U5 ... type discrepancy -> scope_unresolved`, `D1 added`, `U5 removed`, although no
finding changed (usd-ai and hastra have the same kind of spurious finding rows). The source and claim rows are
correct. Second, `amendment_changes` holds only the last amendment, so a later re-render would lose the AC-05 rows.

### 0.2 File scope (HARD)
```
[EDIT] lib/changes.py, lib/runstate.py, lib/render_md.py, lib/schema.py (SKILL_VERSION, schema_doc text for the
       derived key), references/schema.md (regenerated), docs/decisions.md (section 3), tests/unit/test_changes.py,
       tests/unit/test_runstate.py, tests/unit/test_render_md.py, tests/golden/* only if they change (list them),
       tests/unit/* that assert SKILL_VERSION
[REUSE -- DO NOT TOUCH] everything else
```

### 0.3 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-patch-v075.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` =
`45318b7409ea43b7701f360d3a607510e28a06e4`; `git status --porcelain` shows only untracked entries under
`handoff_specs/`; `d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. Changes
- `changes.diff(old_doc, new_doc, match="carried_from")`: new keyword `match` in ("carried_from", "id"). With
  `"id"`, findings are paired by id (added = id only in new, removed = id only in old, changed leaves otherwise; the
  ref is the id; `carried_from` is compared like any other leaf). `"carried_from"` keeps today's behaviour and stays
  the default (seeded change log, Appendix O first part).
- `amendment_changes` becomes the full amendment history: a list of `{"amendment": k, "from": "<run_id>.v<k-1>",
  "to": "<run_id>.v<k>" or "current", "rows": [...]}` for k = 1..m (m = state.amendment), each
  `changes.diff(migrate_to_current(archive/<run_id>.v<k-1>/<slug>.dd.json), <archive v<k> record or the current
  record for k = m>, match="id")`. A missing archive version gives that entry `"rows": []` plus
  `"note": "archive version not found"`. `[]` when m = 0.
- Report Appendix O: after the seeded part, one `### Changes in amendment <k> (<from> -> <to>)` table per entry, in
  k order; an entry with no rows shows `No changes.`
- `SKILL_VERSION = "0.7.5"`.

## 2. Tests
- test_changes: two versions of one run where findings carry legacy `carried_from` values that differ from their ids
  (e.g. D1 carried_from D2, U5 carried_from D1) and nothing changed -> `diff(..., match="id")` is `[]`;
  `match="carried_from"` on the same pair reproduces the old spurious rows (documents why the default is kept for the
  seeded log); a real finding change (type or statement) appears once under its id.
- test_runstate: a run amended twice (amendment 1 with a source correction and a claim change, amendment 2 with no
  content change) -> amendment_changes has two entries; entry 1 has the correction and claim rows; entry 2 has
  `rows: []`; Appendix O shows both headings.
- Version assertions use schema.SKILL_VERSION.

## 3. Decision (append after D90, before "## Validation records")
```
- D91 - Amendment history - 2026-10-21 - Amendment change logs pair findings by id (ids are stable within a run) and keep one entry per amendment, so every earlier amendment's changes stay in the derived file and report.
```

## 4. Build and verify
1. Canary. `git switch -c v075-amendlog`.
2. Implement; regenerate references/schema.md.
3. `python -m pytest -q -rs` -> all pass, no d2 skips; ast (3.11) OK; v0.7.2 scans empty.
4. Commit `fix: amendment change log by id, full amendment history (v0.7.5)` (message file under .scratch\misc\);
   nothing under handoff_specs/; push; ls-remote.
5. Smoke, read-only, with the repo code: for usd-ai, huma, hastra under `C:\web3projects\rwa-dd-reports`, compute in
   memory (write nothing) the amendment history the new code would write for the current final run and print, per
   amendment entry, the row count and the count of finding rows. Expected for amendment 3: huma 0 rows; usd-ai and
   hastra only source (S), claim and the finding rows that really changed (report them).
6. Do NOT deploy. `git status --porcelain` shows only untracked entries under handoff_specs/.

## 5. Return contract
- **A** diff of lib/changes.py and the amendment_changes builder; test names.
- **B** pytest tail; ast; scans; smoke output.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.2: NONE".
- **D** anomalies.

Also write Blocks A-D verbatim to `handoff_specs/results/handoff-patch-v075.result.md` (UTF-8, LF; overwrite on
re-run). Never commit it.
