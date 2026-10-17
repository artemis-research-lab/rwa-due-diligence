# Runtime notes
Run-time constraints, data caveats and the output contract of this skill. This file ships with the skill.
Keep it platform-neutral: no PowerShell, no Windows paths. Developer-session rules belong in CLAUDE.md, which does not ship.

## Constraints
- Python 3.11 or newer, standard library only (v0.1). Later versions add pypdf and the d2 binary (v0.9.0).
- The script writes only inside <root>/<slug>/. Timestamps come only from the script clock.
- No network access from the scripts in v0.1; research is done by the agent with its own tools.

## Data sources and caveats
- Claim status is derived from source origin: first_party sources can only support self_reported;
  legal facts are verified only by regulator, registry, auditor or on-chain sources.
- not_found with evidence means "checked and absent"; not_found without evidence means "not checked".
- Archived sources carry archived=true and a version_date; they may not reflect the current document.

## Output contract
- <slug>.dd.json conforms to schema rwa-dd/1.0 (references/schema.md) and is valid by `dd.py validate`.
- <slug>.report.md is rendered deterministically from <slug>.dd.json; it contains no text that is not in the JSON
  except fixed headings, labels and the legend.
- finalize prints {"project_dir", "outputs", "audit_dir", "scratch_dir", "rounds"} as JSON on stdout.
- <slug>.report.html is one self-contained file: inline CSS (vendored Lism CSS, see references/third-party.md, plus
  report styles), no JavaScript, no external resources; links to sources open in a new tab. It mirrors the Markdown
  report section for section.
