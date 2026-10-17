# Project conventions for Claude Code -- rwa-due-diligence

> Scope: these rules apply to Claude Code sessions. A Chat/Design session that reads this file does so for context only.
> Execution: cloud
> In cloud sessions the shell is Bash on Linux; the "PowerShell not Bash" rule applies to Local sessions only.
> Do not run tools/*.ps1 in a cloud session unless `pwsh` is installed. Never write secrets to the repo.
> Every task ends with a commit; in cloud sessions it also ends with a push. Report branch and full commit hash in Block C.

## SHELL -- Bash on Linux (cloud session)
First tool call: `ls -la | head -20`
This project runs in a cloud environment (Linux, Bash). PowerShell cmdlets do not exist here: do not use them and do not try to install PowerShell.
Use forward-slash paths. Do not run tools/*.ps1 (they are verified on Windows only).
Run Python as `python3`; install dev dependencies with `pip install -r requirements.txt` only if the task needs them.
Never print environment variables, tokens or request headers.
Finish every task with a commit and a push; report branch and full commit hash.

## HANDOFF SPECS -- how I am invoked
"build the project in handoff_specs/<f>.md" / "build the module in handoff_specs/<f>.md" /
"apply the patch in handoff_specs/<f>.md" / "Do the probe in handoff_specs/<f>.md":
1. Read the file with View. 2. Follow verbatim; section 0 + 0.5 canary bind the session.
3. Return the spec's Block A/B/C/D (or probe return contract), no substitutions.
4. VERBATIM sections are copied character-for-character.

## Read-only scope (NEVER violate)
Forbidden symbols: signTransaction, sendTransaction, PrivateKey, Keypair, secretKey,
mnemonic, ethers.Wallet, from web3 import, from viem import.

## Pre-flight
Before any task: `git status --porcelain` must be empty. If not, STOP and report.

## Scratch files
All temporary files go under `.scratch/{probe,build,logs,misc}/` inside this repo. Never use the OS temp folder or any path outside the repo. Never save request headers or `curl -v` output. Write JSON scratch files as UTF-8 via Python.

## Docs
Read `docs/architecture.md` first, in every session. `docs/` files are English. architecture.md holds Purpose, Modules (Responsibility / Input / Output / Depends on), Known Limits, Coding Notes only: no implementation details.

## Skill packaging
A skill package ships only run-time components: `SKILL.md`, `scripts/` and `lib/` (`*.py`), and optionally `references/`, `data/`, `config/` data files and `assets/ (.css .html .tmpl .svg)`. This file, `requirements.txt`, `pytest.ini`, `tests/`, `docs/`, `tools/`, `handoff_specs/`, `.scratch/` and `.claude/` never ship.
Run-time constraints, data caveats and output contracts go in `SKILL.md` or `references/`, never here. Skill code and `SKILL.md` run instructions stay OS-neutral (`pathlib`, "python3, or python on Windows").

## PROJECT LAYOUT
- scripts/dd.py: CLI entry point (argparse); imports lib/ via sys.path.
- lib/schema.py: the only definition of schema rwa-dd/1.0; references/schema.md is generated from it (`python3 scripts/dd.py schema-doc > references/schema.md`) and must be regenerated in the same commit whenever schema.py changes.
- lib/claims.py, lib/validate.py: claim rules and whole-document validation.
- lib/ledger.py, lib/runstate.py: source ledger and run directory contract; the only writers of audit/.
- lib/directives.py, lib/review.py, lib/render_md.py, lib/textutil.py: review loop and Markdown rendering.
- tests/unit: pytest, offline, deterministic (fixed clock injected). tests/golden: byte-exact expected renders.
- Golden files are updated only when a spec says so; never "fix" a failing golden by regenerating it.
