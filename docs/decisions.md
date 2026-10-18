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

## Validation records
- 2026-10-18 - probe-1 renderer bake-off and probe-2 manual DD of usd-ai, huma, hastra accepted in the design session; findings folded into schema rwa-dd/1.0.
- 2026-10-18 - P1 accepted at 903f20f after independent re-run; one test failed only on a Windows checkout (CRLF in fixtures), fixed by D20.
- 2026-10-18 - usd-ai end-to-end run finalized after 3 rounds; final acceptance found admin actions missed by the run (sUSDai upgraded twice, three direct upgrades without timelock), leading to D27-D28.
- 2026-10-18 - usd-ai (amendment 1), huma and hastra finalized and accepted; all three showed rejected searches under section 2, leading to D32.

## Incidents

## Baselines
- 2026-10-18 - P1 cloud build cost about 4 USD of cloud credit (whole-dollar display), no plan-limit change.
- 2026-10-18 - P2 cloud build cost about 3 USD of cloud credit.
- 2026-10-18 - P3 cloud build cost about 4 USD of cloud credit; P1-P3 total about 11 USD.
