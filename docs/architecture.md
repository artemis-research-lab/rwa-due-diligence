# rwa-due-diligence - Architecture

## Purpose
Read-only due diligence on an RWA project from its URL: record legal structure, off-chain yield source and on-/off-chain fund flows as validated, evidence-linked data, and render human-readable reports from that data. It does not score risk and never transacts.

## Modules
### Schema
- Responsibility: Define the rwa-dd/1.0 document, its enums and field limits.
- Input: None.
- Output: The schema definition and its generated reference document.
- Depends on: none.

### Claims and validation
- Responsibility: Decide whether each claim's status is supported by its evidence and whether the whole document is consistent.
- Input: A DD document and its source ledger.
- Output: A list of errors with document paths.
- Depends on: Schema.

### Run directory
- Responsibility: Own the per-project directory, the source ledger, the run state and the round lifecycle.
- Input: Analyst commands (init, add-source, review, directives, finalize, amend).
- Output: Working files, review packets, directive records and final outputs in the project directory.
- Depends on: Schema, Claims and validation, Review loop, Reports.
- Note: A final run can be reopened by an amendment; the previous outputs move to archive/<run_id>.v<m>/.

### Review loop
- Responsibility: Summarise a round for the analyst and turn the analyst's reply into structured directives.
- Input: The working DD document; the analyst's directive text.
- Output: A review packet; parsed directives.
- Depends on: Schema.

### Reports
- Responsibility: Render the DD document into reports without adding content.
- Input: A valid DD document and the round records.
- Output: Markdown report and a self-contained HTML report, with one flow diagram per product.
- Depends on: Schema, Flow diagrams.
- Note: final reports list searches not run in Appendix D, marking the ones the analyst rejected; section 2 lists blocking gaps only.

### Flow diagrams
- Responsibility: Turn each product's fund flows into a diagram with fixed lanes and styles.
- Input: The flows section of a valid DD document.
- Output: One diagram per product, embedded in or linked from the reports.
- Depends on: Schema.

### Research support
- Responsibility: Give the agent a written research method and two read-only helpers for public files.
- Input: The project URL and the analyst's directives.
- Output: Downloaded public files and their extracted text inside the project's scratch area.
- Depends on: Run directory.

## Known Limits
- Research quality depends on public disclosure; private materials enter only through analyst add-source directives.
- Diagrams need the external d2 binary at the pinned version; without it only draft reports can be produced.
- Public information rarely covers issuer identity, fee stacks and loss order; these remain gaps until the analyst adds private material.

## Coding Notes
- The document is the single source of truth; renderers add only fixed headings, labels and the legend.
- Timestamps are produced only by the script clock; the source ledger is append-only and authoritative.
- Nothing is written outside the project directory.
- Rendering is deterministic: identical input gives byte-identical output on every OS.
- Scripts are OS-neutral and use only the standard library unless a decision says otherwise.
