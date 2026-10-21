# handoff-patch-v073 -- rwa-due-diligence v0.7.3: manifest lint count

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. build the patch in handoff_specs/handoff-patch-v073.md"

## 0. Persistent context
- Base: `main` = `5821fbe` (full hash in the canary below). Target: **SKILL_VERSION 0.7.3**; schema stays rwa-dd/2.2.
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v073-manifest` from main, one commit, push it. Do not touch `main`. Do not commit anything under
  `handoff_specs/`. Do NOT deploy. D1-D83 apply; this patch adds D84.

### 0.1 Why
The three v2.2 closure finals record `"lint_warnings": 6` in `<slug>.manifest.json` while lint reports 0 (usd-ai,
huma) and 2 (hastra) warnings. `lib/package.py` line 56 computes `len(lint.lint(doc))`, the number of lint keys (6),
not the number of warnings. verify uses the same function, so it passes while the manifest misstates the check.

### 0.2 File scope (HARD)
```
[EDIT] lib/package.py, lib/schema.py (SKILL_VERSION and, if the manifest is documented there, the check text),
       references/schema.md (regenerated), docs/decisions.md (section 2), tests/unit/test_package.py,
       tests/unit/* that assert SKILL_VERSION
[REUSE -- DO NOT TOUCH] everything else
```

### 0.3 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-patch-v073.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` starts with
`5821fbe` (print the full hash); `git status --porcelain` shows only untracked entries under `handoff_specs/`;
`d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. Change
- In `package.manifest` (and wherever verify builds the same checks), `lint_warnings` = total number of warnings,
  `sum(len(v) for v in lint.lint(doc).values())`, and add `"lint_by_key": {key: count}` (all six keys, sorted) right
  after it. verify compares both.
- `SKILL_VERSION = "0.7.3"`.

## 2. Decision (append after D83, before "## Validation records")
```
- D84 - Manifest lint count - 2026-10-21 - The manifest records the total number of lint warnings and the count per key, not the number of lint keys.
```

## 3. Tests
- test_package: manifest of the clean fixture run has lint_warnings 0 and six zero counts; a run whose record carries
  one known lint warning (for example an amount with as_of null on an L1_L2 edge) has lint_warnings 1 and that key 1;
  verify FAILs when the manifest's lint_warnings is edited.
- Version assertions use schema.SKILL_VERSION.

## 4. Build and verify
1. Canary. `git switch -c v073-manifest`.
2. Implement; regenerate references/schema.md if it changed.
3. `python -m pytest -q -rs` -> all pass, no d2 skips; ast (3.11) OK; v0.7.2 scans empty.
4. Commit `fix: manifest lint count (v0.7.3)` (message file under .scratch\misc\); nothing under handoff_specs/;
   push; ls-remote.
5. Smoke, read-only, with the repo code: for usd-ai, huma and hastra under `C:\web3projects\rwa-dd-reports` print
   `lint` totals per key and the `lint_warnings` value the new code would write (call package.manifest on the loaded
   final record in memory; write nothing). Expected: 0, 0, 2.
6. Do NOT deploy. `git status --porcelain` shows only untracked entries under handoff_specs/.

## 5. Return contract
- **A** diff of lib/package.py; test names.
- **B** pytest tail; ast; scans; smoke output.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.2: NONE".
- **D** anomalies.

Also write Blocks A-D verbatim to `handoff_specs/results/handoff-patch-v073.result.md` (UTF-8, LF; overwrite on
re-run). Never commit it.
