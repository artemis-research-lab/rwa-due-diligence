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
- Input: Analyst commands (init, add-source, review, directives, finalize).
- Output: Working files, review packets, directive records and final outputs in the project directory.
- Depends on: Schema, Claims and validation, Review loop, Reports.

### Review loop
- Responsibility: Summarise a round for the analyst and turn the analyst's reply into structured directives.
- Input: The working DD document; the analyst's directive text.
- Output: A review packet; parsed directives.
- Depends on: Schema.

### Reports
- Responsibility: Render the DD document into reports without adding content.
- Input: A valid DD document and the round records.
- Output: Markdown report (HTML report and flow diagrams in later versions).
- Depends on: Schema.

## Known Limits
- v0.1 has no research automation, HTML report or flow diagrams.
- Public information rarely covers issuer identity, fee stacks and loss order; these remain gaps until the analyst adds private material.

## Coding Notes
- The document is the single source of truth; renderers add only fixed headings, labels and the legend.
- Timestamps are produced only by the script clock; the source ledger is append-only and authoritative.
- Nothing is written outside the project directory.
- Rendering is deterministic: identical input gives byte-identical output on every OS.
- Scripts are OS-neutral and use only the standard library unless a decision says otherwise.
