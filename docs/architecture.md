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
