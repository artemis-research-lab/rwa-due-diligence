# rwa-due-diligence - Architecture

## Purpose
Read-only due diligence on an RWA private-credit project from its URL: map the project onto the Artemis three-layer
model, record entities, interfaces, holder rights, default path, the underlying business and fund flows as validated,
evidence-linked data, and render a Markdown report and diagrams from that data. It does not score risk and never
transacts.

## Research model (rwa-dd/2.0)
- Layers: L1 On-chain Capital Vault, L2 Credit Financing Layer, L3 Underlying Business Layer. Layers are functions;
  an entity may hold functions in several layers and a layer may hold several entities.
- Strategy (T): one financing path from one or more products to an L3 business, with business type, sublayers,
  L3 business facts and the default path (events of default, enforcement, loss waterfall, recovery history).
- Interface (X): one legal edge between holders or entities, kind holder_L1, L1_L2, L2_L3 or within a layer, with the
  framework fields: route (POOL, FUND, DIRECT, WRAPPER) for L1_L2, method (DL, DI, AP, PI, REPO, PT) for L2_L3, legal
  class (DL, DI, AP, PI, FI, EI, OTHER), instrument, currency, counterparty, governing law, claim holder, terms,
  security, collateral, perfection, enforcement, recourse, as-of date.
- Holder rights per product: instrument nature, claim against, look-through, recourse, law, forum, insolvency
  protection, disclaimers.
- Flows: one node set, three views (settlement, claim, repayment), each edge tagged with strategies and interface.
- Evidence flags (CONFIRMED, PARTIALLY_VERIFIED, UNRESOLVED, CONFLICTING) are derived from claim status and
  discrepancy subjects, never entered by hand.
- Research questions A1-F3 (protocol) map to these fields; issuer requests cite the codes they answer.
- Framework completeness K1-K7 per strategy: L1 legal counterparty, L1->L2 legal claim, L2->L3 method, L2->L3
  security, loss waterfall, holder look-through, L3 business.

## Modules
### Schema
- Responsibility: Define the rwa-dd/2.0 document, its enums, coded claims and field limits.
- Input: None.
- Output: The schema definition and its generated reference document.
- Depends on: none.

### Claims and validation
- Responsibility: Decide whether each claim is supported by its evidence and whether the document is consistent,
  including references, coded values and framework coverage rules.
- Input: A DD document and its source ledger.
- Output: A list of errors with document paths.
- Depends on: Schema.

### Framework view
- Responsibility: Derive evidence flags, conflicts, the completeness checklist and holder-to-L3 chain lines.
- Input: A valid DD document.
- Output: Flags per claim, a per-strategy checklist and chain lines.
- Depends on: Schema.

### Migration
- Responsibility: Convert an earlier-schema record into the current schema without inventing classifications.
- Input: An rwa-dd/1.0 document.
- Output: An rwa-dd/2.0 document whose unmapped facts list everything that needs re-mapping.
- Depends on: Schema.

### Run directory
- Responsibility: Own the per-project directory, the source ledger, the run state and the round lifecycle.
- Input: Analyst commands (init, init --seed-from, add-source, review, directives, finalize, amend).
- Output: Working files, review packets, directive records and final outputs in the project directory.
- Depends on: Schema, Claims and validation, Migration, Review loop, Reports, Flow diagrams.
- Note: A final run can be reopened by an amendment; a seeded run reuses the earlier run's sources.

### Review loop
- Responsibility: Summarise a round by framework group and completeness, and turn the analyst's reply into directives.
- Input: The working DD document; the analyst's directive text.
- Output: A review packet; parsed directives.
- Depends on: Schema, Framework view.

### Reports
- Responsibility: Render the DD document into a Markdown report ordered by the framework's mandatory outputs.
- Input: A valid DD document, the round records and the rejected searches.
- Output: Markdown report linking one diagram per strategy and view.
- Depends on: Schema, Framework view, Flow diagrams.
- Note: HTML output is suspended until the curator has reviewed the data model.

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
- Legal documents behind interfaces, holder rights and default paths are rarely public; they enter through analyst
  add-source directives, and gaps stay visible as UNRESOLVED with issuer requests.
- Diagrams need the external d2 binary at the pinned version; without it only draft reports can be produced.
- The framework is a draft classification standard; the skill implements classification and evidence only, no risk
  methodology.

## Coding Notes
- The document is the single source of truth; renderers add only fixed headings, labels and the legend.
- Evidence flags are derived, never stored.
- Timestamps are produced only by the script clock; the source ledger is append-only and authoritative.
- Nothing is written outside the project directory.
- Rendering is deterministic: identical input gives byte-identical output on every OS.
- Scripts are OS-neutral and use only the standard library unless a decision says otherwise.
