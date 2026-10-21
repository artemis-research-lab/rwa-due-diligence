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
- Counting: only stock amounts (balances, position values, outstanding principal) on funding edges, with a data time
  established by the source or the block, outside alternative paths, are summed, one measure per edge, and only within
  the same basis, unit and date. Retrieval times are observed-at metadata, never data times.
- Package: finalize writes a manifest of every output, ledger, expectation, round record and analyst input with
  SHA-256 and execution metadata; `dd.py verify` reproduces the checks from the package.
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
