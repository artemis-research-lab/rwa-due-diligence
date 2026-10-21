# handoff-patch-v074 -- rwa-due-diligence v0.7.4: regulatory filing attribution (curator AC-05)

Run as (CC **Local** session on Windows, working directory `C:\web3projects\rwa-due-diligence`):
"CRITICAL TOOL CHOICE: Use the PowerShell tool, NOT Bash. If unavailable, abort. build the patch in handoff_specs/handoff-patch-v074.md"

## 0. Persistent context
- Base: `main` = `363c067d4acfe3af768fc9c452a8f0bb81160eba` (v0.7.3 plus spec commit). Target: **SKILL_VERSION
  0.7.4**; **SCHEMA stays rwa-dd/2.2**: the only vocabulary change is one added enum value (source origin `filer`),
  which keeps every existing record structurally valid.
- Execution: **Local**, Windows PowerShell 5.1. Canary variant: **LOCAL** (this spec is not committed).
- Branch: create `v074-attribution` from main, one commit, push it. Do not touch `main`. Do not commit anything under
  `handoff_specs/`. Do NOT deploy. D1-D84 apply; this patch adds D85-D89 (section 8).
- Scripts stay OS-neutral Python, standard library only. Read-only skill.
- The accepted v2.2 design, AC-01 to AC-04 controls and all QA1-QA13 rules stay unchanged.

### 0.1 Why (curator AC-05, 2026-10-21)
SEC filings (10-K, 10-Q, 8-K, S-1, 424B4 and exhibits) were registered as `source_type regulator_filing` with source
`origin regulator`, so a company's own disclosure counted as a regulator source: it could verify legal facts
(`LEGAL_VERIFIERS`) and claims took `origin regulator` (USD.AI `X5.legal_class`, `X5.method` on the Corvex 10-Q S172).
The filing channel was conflated with the declarant. The curator requires: document type, assertion origin,
publication source, verification basis and verification status kept distinct; corporate filings attributed to the
filer; regulator-issued records limited to what they establish; a verified claim to have an identifiable
verification basis; no enforceability conclusion from a disclosure of an agreement's existence or terms; and a
permanent regression control (QA14).

Concept map (no field renamed):
```
document_type        = sources[].source_type   (regulator_filing = a document a reporting entity filed with a
                                                 regulator; regulator_registry = a record issued or kept by a
                                                 regulator: register entry, licence, decision, order, filing index)
assertion_origin     = claims[].origin          (unchanged enum; a filer's statement is issuer_documents, borrower or
                                                 independent_party, never regulator)
publication_source   = sources[].url host + source_type (derived; e.g. "sec.gov (regulator_filing)")
verification_basis   = derived per claim (section 3): the cited sources that can verify it
verification_status  = claims[].status and the derived flag (unchanged)
```

### 0.2 Verified shared contracts (base commit)
```
lib/schema.py: ENUMS origin (first_party, regulator, registry, auditor, onchain, third_party, analyst); source_type incl.
  regulator_filing, regulator_registry, legal_doc; SOURCE fields id,url,title,source_type,origin,publisher,
  retrieved_at,fetch,excerpt,excerpt_sha256,archived,version_date,note; QA_RULES QA1..QA13; EXPECT_OPS
lib/claims.py: LEGAL_VERIFIERS; evidence_role(); check_claim(); provenance_errors(); q8_exempt()
lib/ledger.py: read_ledger(path) -> list of source dicts; make_source(index, ...)
lib/validate.py: ledger_errors(doc_sources, ledger) compares doc sources to the ledger entry by entry
lib/changes.py: diff(old_doc, new_doc) (sources: only "S<n> added" rows)
lib/framework.py: resolve(), RESOLVE_PATTERN (E|P|T|X|Z|G|D|C|U|R ids)
lib/qa.py: run(), check_expectation(), EXPECT_KEYS/EXPECT_OPTIONAL
scripts/dd.py: add-source subcommand
```
If any differs, STOP and report.

### 0.3 File scope (HARD)
```
[EDIT] lib/schema.py, lib/claims.py, lib/validate.py, lib/lint.py, lib/ledger.py, lib/framework.py, lib/qa.py,
       lib/changes.py, lib/runstate.py, lib/review.py, lib/render_md.py, lib/package.py (only if a new output field
       must be listed), scripts/dd.py
[EDIT] references/schema.md (regenerated), references/research-protocol.md (VERBATIM 7.1), SKILL.md (VERBATIM 7.2),
       docs/architecture.md (VERBATIM 7.3), docs/decisions.md (section 8)
[EDIT/NEW] tests/fixtures/acme.dd.json and acme.sources.jsonl (only as needed; say what), tests/fixtures/ac05/**
       (NEW positive and negative cases), tests/fixtures/acme.qa-expect.json, tests/golden/* (regenerated; list
       every file), tests/unit/* (new: test_attribution.py)
[REUSE -- DO NOT TOUCH] lib/migrate.py, lib/fetch.py, lib/pdftext.py, lib/directives.py, lib/flow.py, assets/**,
  tools/**, CLAUDE.md, .gitattributes, pytest.ini, .gitignore, handoff_specs/** (except the results file)
```

### 0.4 Canary (LOCAL)
`Get-ChildItem | ConvertTo-Json -Depth 1`; SHA-256 of `handoff_specs/handoff-patch-v074.md` equals the value in the
CC prompt; `git fetch origin`; `git switch main`; `git merge --ff-only origin/main`; `git rev-parse HEAD` =
`363c067d4acfe3af768fc9c452a8f0bb81160eba`; `git status --porcelain` shows only untracked entries under
`handoff_specs/`; `python --version` >= 3.11; `d2 --version` = v0.9.0. Any mismatch -> STOP.

## 1. Vocabulary (lib/schema.py)
- `ENUMS["origin"]` gains `filer` (after `regulator`): "a reporting entity's own document filed with or furnished to
  a regulator; the regulator is only the repository".
- `SKILL_VERSION = "0.7.4"`. schema_doc documents the concept map (0.1), the attribution rules (2), the verification
  basis (3), QA14 and ledger corrections (4). Regenerate references/schema.md.

## 2. Attribution rules (lib/validate.py, lib/claims.py; error texts exact)
Source level (validate, on the document's sources after ledger corrections):
- A1 `source_type regulator_filing` requires origin `filer` or `first_party`:
  `sources[<i>].origin: <S id> is a filing made to a regulator; its origin is the filer (filer or first_party), not regulator (curator AC-05)`.
- A2 origin `regulator` requires `source_type regulator_registry`:
  `sources[<i>].source_type: origin regulator is only for records a regulator issues or keeps (regulator_registry) (curator AC-05)`.
- A3 origin `filer` requires `source_type regulator_filing`:
  `sources[<i>].source_type: origin filer is only for filings (regulator_filing)`.
Claim level (claims.py; claims under audits[] keep their Q8 exemption but not this one):
- A4 claim `origin regulator` requires a cited source with origin regulator; claim `origin registry` requires a cited
  source with origin registry: `<path>: origin <o> requires a <o> source in evidence (curator AC-05)`.
- A5 a `filer` source is never a verifier: `evidence_role` returns `self` when its publisher is the claim subject (as
  now) and otherwise `independent:filer`, but `filer` is excluded from LEGAL_VERIFIERS and from the
  "verified requires an independent source" test (see 3).
- A6 enforceability: for claims at `interfaces[].enforcement`, `interfaces[].perfection`,
  `supports[].enforceability` and `holder_rights[].insolvency_protection`, status `verified` or `inferred` is an error
  when every cited source is a disclosure (origin filer or first_party, or source_type legal_doc):
  `<path>: enforceability is not established by a disclosure of an agreement's existence or terms; use self_reported, third_party_reported (for example a legal opinion) or not_found (curator AC-05)`.
  A claim citing at least one regulator, registry, onchain or tested-auditor source is not caught by A6.

## 3. Verification basis (lib/claims.py, lib/framework.py)
- `claims.verification_basis(parts, claim, sources_by_id)` -> sorted list of cited source ids that can verify this
  claim: origin `regulator`, `registry` or `onchain`; origin `auditor` only when the claim has origin
  auditor_procedure and assurance TESTED (Q8); origin `third_party` only on non-legal paths. Never `filer`,
  `first_party` or `analyst`. Sources whose publisher is the claim subject never count (as now).
- V1 status `verified` requires a non-empty verification basis (replaces the v0.6.0 "verified requires an independent
  source" and the legal-path verifier test, which it subsumes):
  `<path>: verified needs a verification basis (regulator record, registry, on-chain read, tested auditor procedure, or for non-legal facts an independent third party); a filer's disclosure is not one (curator AC-05)`.
- derived.json gains `verification_basis: {claim_id: [source ids]}` for every verified claim (sorted by claim id).
- Report claim cell for verified claims appends `basis S12, S34` inside the source parentheses; Appendix I lists, per
  source, `publication: <host> (<source_type>)` and any ledger correction (4).

## 4. Ledger corrections (lib/ledger.py, scripts/dd.py, lib/validate.py)
The ledger stays append-only. Source attribution is corrected by appending a correction line, never by editing.
- Correction line: `{"correction": "<S id>", "fields": {<field>: <new>}, "previous": {<field>: <old>}, "reason":
  "<20..300 chars>", "corrected_at": "<script clock timestamp>"}`; correctable fields: `source_type`, `origin`,
  `publisher` (at least one; new value differs from the current one; values pass the SOURCE schema).
- `ledger.read_ledger(path)` returns the source list with all corrections applied in file order (the document's
  sources must equal it, as now); `ledger.read_corrections(path)` returns the correction lines. A correction of an
  unknown id or a malformed line is a ContractError naming the line.
- `dd.py correct-source --slug <s> --id <S id> [--source-type T] [--origin O] [--publisher E<n>|none] --reason
  "<text>" --root .` appends a correction and applies it to `audit/dd.work.json` sources (same transaction as
  add-source). Allowed only while the run is open (not in phase final); prints the correction.
- `add-source` refuses A1/A2/A3 violations up front with the same texts.
- `lib/changes.py`: corrections produce rows `ref S<n>, path origin (or source_type, publisher), changed, before,
  after` in the change log.
- New derived key `amendment_changes`: when `state.amendment` >= 1, diff (lib/changes.diff, incl. source rows) between
  the previous final version of this run (`archive/<run_id>.v<m-1>/<slug>.dd.json`, m = current amendment) and the
  current record; `[]` otherwise. Report Appendix O gets a second part `Changes in amendment <m>` listing these rows.
  This preserves the previous and revised classification of every affected claim and source (curator section 5).

## 5. QA14 and expectations (lib/qa.py, lib/framework.py)
- QA14 `attribution`: offenders = sources violating A1-A3 plus claims violating A4, A6 or V1 (reuse the validate and
  claims functions). Rule text: `No filing is attributed to a regulator, no regulator or registry origin lacks such a
  source, every verified claim has a verification basis that excludes filer disclosures, and no enforceability claim
  rests only on a disclosure (curator AC-05).` Results list QA1..QA14 then E:<id>.
- `RESOLVE_PATTERN` and resolve accept `S<n>` (a source object; fields `S172.origin`, `S172.source_type`).
- New expectation op `status_in` (value: non-empty list of claim statuses).
- `dd.py qa` help: QA1-QA14.

## 6. Fixtures and tests (offline)
- `tests/fixtures/ac05/`: small documents (or patch functions over acme) with ledgers, covering:
  negative: filing with origin regulator (A1); a 10-Q-only claim with origin regulator (A4); a legal claim verified
  only by a filer source (V1); an enforcement claim inferred only from a first-party legal_doc (A6); origin regulator
  on a non-registry source (A2); origin filer on a project_docs source (A3);
  positive: regulator_registry licence record verifying an entity's licence (verified, basis [S]); registry-verified
  jurisdiction; filer statement self_reported with origin borrower; filer statement third_party_reported with origin
  independent_party; on-chain verified amount; enforcement self_reported from a filing; tested auditor procedure
  verifying a balance.
- test_attribution: each case gives exactly the expected error or none; QA14 pass/fail; verification_basis values;
  correct-source (append, fold, refuse unknown id, refuse same value, refuse in phase final, ledger file is append
  only: earlier bytes unchanged); read_ledger fold order; changes rows for corrections; amendment_changes against an
  archived previous version.
- acme: if A1-A6 or V1 reject a fixture claim, fix the fixture through a correction line in acme.sources.jsonl where
  it is a source attribution, and say what changed. acme.qa-expect.json: add one `S<n>.origin` and one `status_in`
  expectation.
- Goldens regenerated; list every file.

## 7. VERBATIM blocks (each old block must be found exactly once; otherwise STOP)

### 7.1 references/research-protocol.md
old:
```
- origin is about who produced the source: first_party, regulator, registry (company, lien and fund registries,
  GLEIF), auditor, onchain (chain state, a block explorer or an indexer reading it), third_party, analyst.
```
new:
```
- origin is about who produced the source: first_party, regulator, filer, registry (company, lien and fund
  registries, GLEIF), auditor, onchain (chain state, a block explorer or an indexer reading it), third_party,
  analyst. A 10-K, 10-Q, 8-K, S-1, prospectus or exhibit filed by a company is source_type regulator_filing with
  origin filer (first_party when the filer is the project itself): the regulator only hosts it. Origin regulator is
  only for records the regulator itself issues or keeps (register entries, licences, decisions, orders, filing
  indexes: source_type regulator_registry), and they establish only what the record states (curator AC-05).
```
old:
```
- Legal facts (entities, interfaces, holder_rights, supports, eligibility) are verified only by regulator, registry,
  auditor or onchain sources, and only within the scope those sources cover. On-chain confirmation of pool receipts
```
new:
```
- Every verified claim needs a verification basis: a regulator record, a registry entry, an on-chain read, a tested
  auditor procedure, or for non-legal facts an independent third party. A company's filing proves that the company
  said it, not that it is true: classify its statements as the company's (self_reported with origin
  issuer_documents or borrower when the filer is a party, third_party_reported with origin independent_party when it
  is not) unless another source verifies them. An agreement's existence or terms in a disclosure never establish its
  enforceability, perfection or insolvency protection. Correct a wrongly registered source with dd.py
  correct-source (the ledger records the previous and revised attribution); never re-register it.
- Legal facts (entities, interfaces, holder_rights, supports, eligibility) are verified only by regulator, registry,
  auditor or onchain sources, and only within the scope those sources cover. On-chain confirmation of pool receipts
```

### 7.2 SKILL.md
old:
```
   `dd.py pdf-text` for PDFs. Edit `audit/dd.work.json` only; run `dd.py validate` until it exits 0, then
```
new:
```
   `dd.py pdf-text` for PDFs. Correct a wrongly attributed source only with `dd.py correct-source` (append-only).
   Edit `audit/dd.work.json` only; run `dd.py validate` until it exits 0, then
```

### 7.3 docs/architecture.md
old:
```
- Evidence: each claim has a status (six derived flags), the asserting origin, the publication sources and the
  assurance scope, so a statement quoted by an auditor is not mistaken for audited fact.
```
new:
```
- Evidence: each claim has a status (six derived flags), the asserting origin, the publication sources and the
  assurance scope, so a statement quoted by an auditor is not mistaken for audited fact. A company filing is
  attributed to its filer, not to the regulator that hosts it; every verified claim has a derived verification basis
  of sources able to verify it; source attribution is corrected by append-only ledger corrections.
```

## 8. Decisions (append after D84, before "## Validation records")
```
- D85 - Filer origin - 2026-10-21 - Source origin gains filer: company filings made to a regulator are the filer's documents; origin regulator is limited to records the regulator issues or keeps (curator AC-05).
- D86 - Verification basis - 2026-10-21 - A verified claim needs a derived verification basis (regulator record, registry, on-chain read, tested auditor procedure, or an independent third party for non-legal facts); filer and first-party sources never verify.
- D87 - Enforceability - 2026-10-21 - Enforcement, perfection, enforceability and insolvency-protection claims are never verified or inferred from disclosures alone.
- D88 - Ledger corrections - 2026-10-21 - Source attribution is corrected by append-only correction lines (dd.py correct-source) that keep the previous value; read_ledger folds them.
- D89 - QA14 - 2026-10-21 - QA14 attribution asserts D85-D87; derived.json carries verification_basis and amendment_changes.
```
Validation records, append:
`- 2026-10-21 - Curator closed AC-01 to AC-04; AC-05 (regulatory filing attribution) implemented in v0.7.4.`

## 9. Build and verify (PowerShell, Local)
1. Canary 0.4. `git switch -c v074-attribution`.
2. Implement 1-8; regenerate references/schema.md and goldens with a script under `.scratch/build/`.
3. `python -m pytest -q -rs` -> all pass, no d2 skips; ast (3.11) OK; v0.7.2 scans empty.
4. Commit (message file under .scratch\misc\): `feat: regulatory filing attribution, verification basis, ledger
   corrections, QA14 (v0.7.4)`. Nothing under handoff_specs/. Push; ls-remote.
5. Fresh clone into `C:\web3projects\_v074fresh`; pytest; same counts; delete it.
6. Smoke, read-only on copies: copy `C:\web3projects\rwa-dd-reports\usd-ai`, `huma`, `hastra` into
   `.scratch\build\smoke074\` (delete first if present). For each, with the repo code on the copied final record and
   ledger: run validate and QA14 and report (a) counts of A1/A2/A3 source errors with the source ids, (b) claims failing
   A4, A6 or V1 with claim ids, (c) the number of verified claims whose verification basis would change. Do not edit,
   amend or finalize the copies. Leave the folder in place.
7. Do NOT deploy. `git status --porcelain` shows only untracked entries under handoff_specs/.

## 10. Return contract
- **A** files table (every golden with reason); A1-A6, V1 and QA14 code with texts; verification_basis; ledger
  correction format, fold and CLI; changes rows; amendment_changes; fixture cases list; acme changes.
- **B** pytest tails (working copy, fresh clone); ast; scans; smoke outputs per project.
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, `git status --porcelain`, "files outside 0.3: NONE".
- **D** anomalies (Benign / Needs decision / Not covered).

Also write Blocks A-D verbatim to `handoff_specs/results/handoff-patch-v074.result.md` (UTF-8, LF; overwrite on
re-run). Never commit it.
