# rwa-due-diligence - Decisions and Records

## Decisions
Format: `D<n> - <title> - <date> - <one-line decision and why>`
- D1 - CC-only skill - 2026-10-18 - Built in cloud sessions, run in Claude Code Local on Windows, because research needs unrestricted network and browser access.
- D2 - JSON is canonical - 2026-10-18 - Markdown and HTML are deterministic renders of dd.json; no AI in rendering, so reports cannot drift from the data.
- D3 - Claim model - 2026-10-18 - Every fact is a Claim with status verified/self_reported/inferred/not_found, evidence, subject and note.
- D4 - No risk scoring - 2026-10-18 - The skill records facts, gaps, discrepancies and structural changes; assessment belongs to the risk curator.
- D5 - Run-time dependencies - 2026-10-18 - Python stdlib; pypdf for PDF text (v0.4); d2 v0.9.0 binary for diagrams (v0.3).
- D6 - HTML report - 2026-10-18 - One self-contained file, no JavaScript, vendored and pinned Lism CSS (v0.2).
- D7 - Repo privacy - 2026-10-18 - Private repository; DD outputs never enter it.
- D8 - Report directory contract - 2026-10-18 - <root>/<slug>/ holds final outputs, audit/ and .scratch/; finalize reports the project directory and output paths.
- D9 - Validation targets - 2026-10-18 - usd-ai, huma, hastra (probe-2 baselines).
- D10 - Multi-round review loop - 2026-10-18 - Review packet, analyst directives, next round; only the analyst finalizes.
- D11 - Flow diagrams - 2026-10-18 - D2 v0.9.0 with ELK, lanes as containers without grid, one diagram per product; output is byte-identical across Windows and Linux.
- D12 - Lanes - 2026-10-18 - offchain, boundary, onchain; boundary holds conversion, bridge and custody hand-off points.
- D13 - Script-only timestamps - 2026-10-18 - The model never writes a time; add-source stamps it and the ledger is authoritative (probe-2 found estimated timestamps).
- D14 - Per-claim independence - 2026-10-18 - Derived from source origin and publisher vs claim subject; third-party sources cannot verify legal facts.
- D15 - Research etiquette - 2026-10-18 - Honest User-Agent; respect ToS automated-access clauses and robots.txt; public registry searches allowed without login, personal data or CAPTCHA; browser fallback is read-only.
- D16 - Budgets - 2026-10-18 - Round 1: 60 fetch/search calls; later rounds: 20 (probe-2 measured 70-80 calls and 17-25 minutes per target).
- D17 - Bounded free text - 2026-10-18 - Free text only in declared fields with maximum lengths; everything is escaped on render.
- D18 - Renderer registry - 2026-10-18 - Reports are registered renderers over the same document; HTML mirrors Markdown section for section and is tested for parity.
- D19 - HTML safety - 2026-10-18 - All document text is HTML-escaped and ASCII-encoded; only http(s) source URLs become links; the page has no script, no external resource and no event attribute.
- D20 - Line endings - 2026-10-18 - Text data files (json, jsonl, txt, html, css, svg, tmpl) are LF in the repository on every OS (found when a Windows checkout broke a byte-exact fixture test).
- D21 - Diagram pipeline - 2026-10-18 - D2 source is built only from schema ids and a restricted label alphabet; d2 v0.9.0 runs as a subprocess with explicit flags (ELK, theme 0) so environment variables cannot change output; the SVG is sanitised before embedding.
- D22 - Version per phase - 2026-10-18 - Every phase spec sets SKILL_VERSION explicitly (v0.3.0 for P3).
- D23 - Cloud branches - 2026-10-18 - Cloud sessions push only their assigned session branch; specs do not name branches and acceptance is anchored on the commit hash.
- D24 - Fetch helper - 2026-10-18 - The only network code is dd.py fetch-file: HTTPS GET, honest User-Agent, host and redirect checks, 25 MB cap, atomic write into .scratch/raw.
- D25 - PDF text - 2026-10-18 - pypdf, pinned, optional at import time; missing pypdf is exit code 4 with the install command.
- D26 - Windows verification - 2026-10-18 - Code built in cloud sessions is accepted only after a fresh-clone test run on Windows (P1-P3 each failed there first: CRLF twice, temp directory once).
- D27 - Amendments - 2026-10-18 - A final run is corrected with dd.py amend: outputs move to archive/<run_id>.v<m>/, one research round reopens with a 10-call budget, the schema is unchanged and the amendment is recorded in audit and shown in the reports.
- D28 - Admin history first - 2026-10-18 - Once an admin Safe is known, its executed transaction history (Safe Transaction Service) is read before log scans or bisection; every event of a transaction is accounted for.
- D29 - Call accounting - 2026-10-18 - One JSON-RPC batch of at most 50 requests counts as one call; reading cached files is free.
- D30 - Issuer questions - 2026-10-18 - Questions only the issuer can answer go to open_questions, never to next_searches.
- D31 - Analyst evidence - 2026-10-18 - The validator rejects a verified claim that cites an analyst source.
- D32 - Searches not run - 2026-10-18 - Final reports show remaining next searches only in Appendix D, marked rejected or not run; section 2 lists blocking gaps only. Draft renders are unchanged.
- D33 - Analyst replies - 2026-10-18 - A reply that does not parse as directives is kept and returned to the analyst with the parse errors; the agent never rewrites it into directives.
- D34 - Analyst downloads - 2026-10-18 - Files viewable only in the browser are requested from the analyst after the review packet as download lines and enter the run through add-source.
- D35 - Terms per domain - 2026-10-18 - Terms of Use and robots.txt are read for every domain before any scripted fetch from it.
- D36 - Address lint - 2026-10-18 - dd.py lint warns on EVM addresses that are all lowercase or all uppercase; it checks case shape only, not the EIP-55 checksum.
- D37 - Three-layer model - 2026-10-19 - The research model follows the Artemis Three-Layer Private Credit & RWA Business Model Framework (Draft v0.1): L1 vault, L2 credit financing, L3 underlying business, as functions, not entities.
- D38 - Schema 2.0 - 2026-10-19 - rwa-dd/2.0 replaces relationships with typed interfaces (route, method, legal class and the framework edge fields), adds strategies, holder rights, default path, L3 business, flow views and issuer requests; 1.0 records are migrated, not patched.
- D39 - Coded claims - 2026-10-19 - Classification codes are claims with evidence; null when not established; the validator checks their values against the framework enums.
- D40 - Derived flags - 2026-10-19 - CONFIRMED, PARTIALLY_VERIFIED, UNRESOLVED and CONFLICTING are derived from claim status and discrepancy subjects, never stored.
- D41 - Completeness - 2026-10-19 - The packet and report show a per-strategy checklist K1-K7 mirroring the framework's mandatory outputs.
- D42 - Seeded runs - 2026-10-19 - init --seed-from archives the old run, copies its ledger byte for byte and starts from a converted record; cached downloads stay in .scratch.
- D43 - Question codes - 2026-10-19 - Research questions A1-F3 are the shared vocabulary of the protocol, issuer requests and curator feedback.
- D44 - HTML suspended - 2026-10-19 - The HTML renderer is removed until the curator has reviewed the data model; Markdown is the only report.
- D45 - Diagrams per strategy and view - 2026-10-19 - One diagram per strategy and view (settlement, claim, repayment); layout engine unchanged pending the layout decision.
- D46 - No risk methodology - 2026-10-19 - The skill records classification and evidence only; no ratings, scores, thresholds, limits or loss estimates.
- D47 - Chain lines - 2026-10-20 - Chain lines follow within-layer hops and continue to L3 ultimate obligors (L3-O); node labels show the position on the path.
- D48 - L3-O - 2026-10-20 - Ultimate obligors stay layer L3 with role ultimate_obligor and are linked by within_L3 interfaces; a separate schema layer waits for curator feedback.
- D49 - Holder-rights subjects - 2026-10-20 - Holder-rights claims have the subject path P<n>.holder_rights.<field>, so discrepancies can flag them CONFLICTING.
- D50 - Subject field names - 2026-10-20 - Subject field names may contain digits after the first letter.
- D51 - No self-loops - 2026-10-20 - An interface's from and to must differ.
- D52 - Schema 2.1 - 2026-10-20 - rwa-dd/2.1 implements the curator's data-model revisions; 2.0 records are migrated by init --seed-from, never patched.
- D53 - Components - 2026-10-20 - Strategies carry a component (CORE_CREDIT, LIQUIDITY_SLEEVE, DEFI_LENDING); completeness and the five questions apply to core credit only; sleeves never get an invented L3.
- D54 - Protocol entitlement - 2026-10-20 - PROTOCOL_ENTITLEMENT is a legal claim class for pool receipts; a POOL route with DL, DI, AP or PI needs a contract source (lint).
- D55 - Alternatives - 2026-10-20 - Competing legal paths share an alternative group and are excluded from counting.
- D56 - Amounts - 2026-10-20 - Funding edges record amount and amount basis; only gross funded amounts outside alternatives are summed.
- D57 - Supports - 2026-10-20 - Credit enhancement and yield support are supports (Z), not interfaces or waterfall steps.
- D58 - Asset sales - 2026-10-20 - Loan sales after origination are asset_sale interfaces; a transferee is not an L3.
- D59 - L3-O - 2026-10-20 - L3-O is a layer value with roles contractual_obligor, cash_flow_source and offtaker_customer, linked by L3_L3O interfaces; migration maps ultimate_obligor to cash_flow_source.
- D60 - Six statuses - 2026-10-20 - Claim status adds third_party_reported; flags are CONFIRMED, SELF_REPORTED, THIRD_PARTY_REPORTED, INFERRED, UNRESOLVED, CONFLICTING.
- D61 - Scope checks - 2026-10-20 - A discrepancy needs a same-scope note; scope_unresolved findings never flag claims; finalize refuses migrated placeholders.
- D62 - Material findings - 2026-10-20 - Findings carry a material flag; material findings open the report.
- D63 - Reader report - 2026-10-20 - The Markdown report has six reader sections (curator Q7) with detail in appendices A-M.

## Validation records
- 2026-10-18 - probe-1 renderer bake-off and probe-2 manual DD of usd-ai, huma, hastra accepted in the design session; findings folded into schema rwa-dd/1.0.
- 2026-10-18 - P1 accepted at 903f20f after independent re-run; one test failed only on a Windows checkout (CRLF in fixtures), fixed by D20.
- 2026-10-18 - usd-ai end-to-end run finalized after 3 rounds; final acceptance found admin actions missed by the run (sUSDai upgraded twice, three direct upgrades without timelock), leading to D27-D28.
- 2026-10-18 - usd-ai (amendment 1), huma and hastra finalized and accepted; all three showed rejected searches under section 2, leading to D32.
- 2026-10-19 - Curator feedback on the usd-ai, huma and hastra reports: reports must follow the three-layer framework; HTML hard to read (deferred).
- 2026-10-20 - Seeded re-maps of usd-ai, huma and hastra (rwa-dd/2.0): layer convention L1 vault and legal entity, L2 credit provider, L3 borrower running the business, L3-O its paying customers; renderer and validator gaps fixed in v0.5.1.
- 2026-10-20 - Curator review of v2 samples: architecture accepted conditionally; revisions implemented in v0.6.0.

## Incidents

## Baselines
- 2026-10-18 - P1 cloud build cost about 4 USD of cloud credit (whole-dollar display), no plan-limit change.
- 2026-10-18 - P2 cloud build cost about 3 USD of cloud credit.
- 2026-10-18 - P3 cloud build cost about 4 USD of cloud credit; P1-P3 total about 11 USD.
