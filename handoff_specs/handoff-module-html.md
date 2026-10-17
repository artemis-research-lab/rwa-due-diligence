# handoff-module-html -- rwa-due-diligence P2: HTML report (Lism CSS) + P1 carry-over fixes C1-C5

Run as (CC **cloud** session, environment `web3-readonly`, repo `artemis-research-lab/rwa-due-diligence`):
"build the module in handoff_specs/handoff-module-html.md"

## 0. Persistent context
- Base: `main` at `903f20ff1a87ef3722de638400b8ead79a294511` (v0.1.0, accepted). Target: v0.2.0.
- Execution: cloud (Linux, Bash, python3). Run-time target: Claude Code Local on Windows, Python >= 3.11. Code stays OS-neutral, stdlib only.
- Branch `p2-html`, one commit, push the branch, do not touch `main`.
- Locked decisions D1-D17 in docs/decisions.md apply; reference by ID. This module implements D6.

### 0.2 Verified shared contracts (actual code at the base commit -- do not guess)
```
lib/runstate.py
  RENDERERS = [("report.md", render_md.render)]       # (suffix, fn(doc, rounds) -> str); finalize and render_draft iterate it
  Project.output(suffix) -> <dir>/<slug>.<suffix>;  Project.write_text(path, text) -> path (UTF-8 bytes, no newline translation)
  render_draft(root, slug) -> writes .scratch/draft/<slug>.<suffix> for every renderer
  finalize(root, slug, clock) -> writes <slug>.dd.json + one file per renderer; returns {"project_dir","outputs","audit_dir","scratch_dir","rounds"}
lib/render_md.py
  MARKERS = {"verified":"V","self_reported":"S","inferred":"I","not_found":"N"}
  fmt_value(value) -> str (Markdown-escaped); claim_cell(claim) -> str; product_title(product) -> str
  render(doc, rounds=()) -> str ; rounds = [(k, directives_text), ...]
  section order: metadata, DRAFT banner, 1..14, Appendix A, B, C (LEGEND)
lib/textutil.py
  clip(text, limit); md_text(text, limit=None); has_control(text); dump_json(value); id_key(item); finding_line(f); search_line(s)
lib/schema.py
  node "ref": Pattern(r"^((E|P)[1-9][0-9]*|0x[0-9a-fA-F]{1,64})$", ...)   (line ~290)   <- C1 changes this
  CLAIM_VALUE_STR_MAX, CLAIM_NOTE_MAX; iter_claims; format_path; order_like_schema
```
The HTML renderer must mirror the Markdown renderer's section order and content. It may import `fmt_value`-independent helpers from render_md only for non-escaping logic (MARKERS, ordering); every string that reaches HTML is escaped by the new html helpers, never by md_escape.

### 0.4 File scope (HARD)
```
[NEW]  lib/render_html.py                 HTML renderer
[NEW]  assets/report.html.tmpl            page skeleton with 4 markers (3.2)
[NEW]  assets/report.css                  our own styles, every class prefixed dd-
[NEW]  assets/lism-css-<version>.min.css  vendored Lism CSS, exact npm version, unmodified bytes except LF line endings
[NEW]  references/third-party.md          Lism CSS name, version, npm tarball sha512 (integrity), file sha256, MIT licence text
[NEW]  tests/unit/test_render_html.py
[NEW]  tests/unit/test_lineendings.py     (C4)
[NEW]  tests/golden/acme.report.html
[EDIT] lib/runstate.py                    RENDERERS gains ("report.html", render_html.render); nothing else
[EDIT] lib/textutil.py                    add html helpers (3.3); existing functions unchanged
[EDIT] lib/schema.py                      C1 ref pattern; C2 rule if it lives here
[EDIT] lib/claims.py / lib/validate.py    C2 (whichever holds claim rules)
[EDIT] lib/runstate.py                    C5 init refusal message (same file as above)
[EDIT] references/schema.md               regenerated
[EDIT] tests/fixtures/acme.dd.json, tests/golden/acme.report.md, tests/golden/acme.review.md   ONLY if C1/C2 force a fixture change (3.5)
[EDIT] tests/unit/test_validate.py, tests/unit/test_claims.py, tests/unit/test_runstate.py, tests/unit/test_cli.py  new cases for C1, C2, C5 and the HTML output path
[EDIT] .gitattributes                     C4
[EDIT] pytest.ini                         C3
[EDIT] SKILL.md                           C5 lines + HTML output mention (4.1 VERBATIM)
[EDIT] references/runtime.md              4.2 VERBATIM
[EDIT] docs/architecture.md               4.3 VERBATIM (Reports module and Known Limits only)
[EDIT] docs/decisions.md                  4.4 VERBATIM appends
[REUSE -- DO NOT TOUCH] tools/**, lib/render_md.py, lib/ledger.py, lib/directives.py, lib/review.py, scripts/dd.py, requirements.txt, CLAUDE.md, handoff_specs/**
```

### 0.5 Canary
`ls -la | head -20`; `git status --porcelain` empty; `git rev-parse HEAD` equals the base commit OR its parent chain is base + exactly one commit that only adds `handoff_specs/handoff-module-html.md` (verify with `git diff --stat 903f20f HEAD`). Anything else -> STOP.

## 1. Motivation
D6: risk curators read an HTML report. It must be one self-contained file with no JavaScript, styled with vendored, pinned Lism CSS, rendered deterministically from dd.json exactly like the Markdown report. The P1 acceptance review also found five carry-over fixes (C1-C5), applied here.

## 2. Carry-over fixes
- **C1** Flow node `ref` accepts any chain address: pattern `^((E|P)[1-9][0-9]*|[A-Za-z0-9]{1,64})$`. Add tests: a base58 Solana address (44 chars), a Provenance `pb1...` bech32 address, and an EVM `0x...` address are valid; `0x` with a space, a 65-char string and `E0` are invalid.
- **C2** A claim with status verified, self_reported or inferred must have a non-null value. Error text: `<path>: <status> requires a non-null value`. Add one negative test per status.
- **C3** `pytest.ini` gains `addopts = --basetemp=.scratch/build/pytest` (keep the existing markers block unchanged).
- **C4** `.gitattributes` gains, after the existing `*.sh` line: `*.json text eol=lf`, `*.jsonl text eol=lf`, `*.txt text eol=lf`, `*.html text eol=lf`, `*.css text eol=lf`, `*.svg text eol=lf`, `*.tmpl text eol=lf` (one per line; `tools/** -text` must remain the last rule). Run `git add --renormalize .` before committing. New test `test_lineendings.py`: no `\r` byte in any file under `tests/fixtures`, `tests/golden`, `assets`, `references`.
- **C5** `init` refusing on an existing unfinished run prints: `run exists (phase <phase>); use "dd.py status" to inspect or --new-run to archive it and start again` (exit 3). SKILL.md lines in 4.1.

## 3. HTML report

### 3.1 Lism CSS vendoring
- `npm view lism-css version` -> use that exact version V. `npm pack lism-css@V` into `.scratch/build/`, extract, take the package's main stylesheet (the file the README loads via CDN: `dist/css/main.css`; if a minified sibling exists use it, otherwise use main.css). Copy to `assets/lism-css-V.min.css` (name keeps `.min` even if unminified, state which in third-party.md). Do not edit the content; only LF normalisation via .gitattributes.
- `references/third-party.md`: package name, version V, the npm `dist.integrity` (sha512) from `npm view lism-css@V dist.integrity`, the sha256 of the committed asset, the source path inside the tarball, and the package's LICENSE text verbatim.
- If npm cannot reach the registry: STOP and report (do not fetch from a CDN; the cloud environment allows package managers only).
- Allowed classes: an HTML `class` token is allowed only if it starts with `dd-` (defined in assets/report.css) or occurs as a class selector in the vendored Lism file. Test enforces this (3.6 #4). Use Lism for layout primitives (stack/flow spacing, container width, grid) and typography tokens as found in the vendored file; use `dd-` classes for everything report-specific.

### 3.2 Template `assets/report.html.tmpl`
Exactly these four markers, each exactly once: `<!--DD:TITLE-->`, `<!--DD:LISM_CSS-->`, `<!--DD:REPORT_CSS-->`, `<!--DD:BODY-->`. The renderer reads the template and CSS files as UTF-8 from `<skill root>/assets/` (skill root = parent of `lib/`), replaces each marker by plain `str.replace` (count must be 1, else raise), and inlines both CSS files inside one `<style>` element each. Skeleton:
```
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="rwa-due-diligence">
<title><!--DD:TITLE--></title>
<style><!--DD:LISM_CSS--></style>
<style><!--DD:REPORT_CSS--></style>
</head>
<body>
<!--DD:BODY-->
</body>
</html>
```

### 3.3 Escaping (lib/textutil.py additions)
- `html_text(text, limit=None)`: clip, replace control chars and CR/LF by a space, `html.escape(..., quote=True)`, then encode non-ASCII as numeric character references (`.encode("ascii", "xmlcharrefreplace").decode("ascii")`).
- `html_url(url)`: return the escaped URL only if it starts with `https://` or `http://` (case-insensitive) and contains no control character or whitespace; otherwise return None (the renderer then shows the URL as text, not a link).
- Every string from the document goes through `html_text`; links are `<a href="{html_url}" rel="noopener noreferrer nofollow" target="_blank">`. No other attribute ever receives document text, except `id` attributes built from schema ids (validated patterns).

### 3.4 Page structure (mirror of the Markdown report)
```
<main class="dd-report [lism container class]">
  <header class="dd-header">  h1 title; metadata as a <dl class="dd-meta"> (same fields as the MD table);
                              when draft: <p class="dd-banner dd-banner--draft">DRAFT -- not finalized</p></header>
  <nav class="dd-toc"> ordered list of links to every section id </nav>
  <section id="s1" ...> h2 "1. Executive summary" ... </section>  ... through s14, then id="appendix-a", "appendix-b", "appendix-c"
</main>
```
- Same headings, same section order, same rows and same "none" handling as render_md (use the text `none` in a `<p class="dd-none">`).
- Tables: `<div class="dd-table-wrap"><table class="dd-table">` with `<thead>`; the wrapper scrolls horizontally on narrow screens.
- Claim cell: `<span class="dd-claim">VALUE <span class="dd-badge dd-badge--v|s|i|n|nq" title="verified|self_reported|inferred|not_found|not_found (not searched)">V|S|I|N|N?</span> <span class="dd-ev">(S1, S4)</span> <span class="dd-note">-- note</span></span>`; evidence ids link to `#src-S1` etc. Sources section rows carry `id="src-S<n>"`.
- Section 2 (blocking gaps) renders as a highlighted panel `dd-panel dd-panel--blocking`; it is the first content after the summary.
- Fund flows: per product `<h3>`, then `<figure class="dd-flow" id="flow-P<n>"></figure>` placeholder (EMPTY in P2; P3 fills it with an inline SVG), then the nodes table and the edges table. Edge-kind cells get `dd-kind dd-kind--<edge_kind>`.
- Appendix A: per round `<h3>Round k</h3><pre class="dd-pre">` escaped directives text (CRLF -> LF as in MD).
- Appendix C legend: the same legend lines as MD plus a badge key.
- `report.css` design: light theme only; system font stack; max content width ~ 72rem; badges V #15803d / S #b45309 / I #1d4ed8 / N #6b7280 / N? #6b7280 dashed border, white text except N? (outlined); edge kinds use the D11 style map colours (subscription/redemption #2563eb, yield #16a34a, fee #6b7280, custody #9333ea, conversion #0891b2, collateral #b91c1c); blocking panel with a left border #b91c1c; `@media print` hides the TOC, removes table scrolling, avoids breaking table rows; `@media (max-width: 40rem)` stacks the metadata list. No `url(`, no `@import`, no web fonts in report.css.

### 3.5 Fixture changes
If C1/C2 make the acme fixture invalid, fix the fixture minimally and regenerate the affected goldens; show the full diff of every changed golden in Block A. Add one flow node with a Solana-style `ref` to the fixture only if the goldens must be regenerated anyway; otherwise add it in a separate test document inside the test, not in the fixture. Never regenerate a golden for any other reason.

### 3.6 Tests (tests/unit/test_render_html.py and others)
1. Golden: render of acme equals `tests/golden/acme.report.html` byte for byte; two renders identical.
2. Self-contained, no JS: output contains no `<script`, no `<link`, no `<iframe`, no `<object`, no `<embed`, no ` on[a-z]+=` attribute, no `javascript:`, no `@import`, no `url(` outside the vendored Lism block if Lism contains any (assert report.css has none), and no `src=` attribute at all.
3. Escaping: a document whose executive summary, an entity name and a note contain `<script>alert(1)</script>`, `" onmouseover="x`, `&`, a newline and a non-ASCII character renders those as escaped text (assert raw forms absent, escaped forms present), and the output body is ASCII.
4. Class allowlist: every class token in the output is `dd-*` and defined in report.css, or appears as a class selector in the vendored Lism file.
5. Links: a source with `javascript:alert(1)` as url renders no `<a>` for it; an https source renders `rel="noopener noreferrer nofollow"`; every `#src-S<n>` and `#s<n>` link target exists in the page (no dangling anchors).
6. Structure parity with MD: the list of h2 headings in HTML equals the list of `## ` headings in the MD render of the same document; same for h3 headings.
7. Draft banner present iff status draft; DRAFT absent in a finalized document.
8. Integration: CLI e2e from P1 now finalizes three outputs (`dd.json`, `report.md`, `report.html`), all inside the project dir; `render` writes the draft HTML into `.scratch/draft/`.
9. Asset integrity: sha256 of `assets/lism-css-V.min.css` equals the value recorded in references/third-party.md.
10. C1, C2, C4, C5 tests as listed in section 2.

## 4. VERBATIM blocks

### 4.1 SKILL.md -- three exact edits
(a) In the description, replace `writes a validated JSON record plus a Markdown report (HTML report and flow diagrams in later` / `versions)` with: `writes a validated JSON record, a Markdown report and a self-contained HTML report (flow diagrams in a later` / `version)` keeping the line breaks of the original.
(b) In "## Workflow" step 5, after the existing sentence add a new line:
```
   The outputs are <slug>.dd.json, <slug>.report.md and <slug>.report.html.
```
(c) Append to "## Hard rules":
```
Directive text must not contain the character "|" (it separates commands). If init refuses because a run exists,
run `dd.py status` and ask the user whether to continue that run or start again with --new-run.
```

### 4.2 references/runtime.md -- append to "## Output contract"
```
- <slug>.report.html is one self-contained file: inline CSS (vendored Lism CSS, see references/third-party.md, plus
  report styles), no JavaScript, no external resources; links to sources open in a new tab. It mirrors the Markdown
  report section for section.
```

### 4.3 docs/architecture.md -- in "### Reports", replace the Output line with
```
- Output: Markdown report and a self-contained HTML report (flow diagrams in a later version).
```
and in "## Known Limits" replace the first bullet with
```
- v0.2 has no research automation or flow diagrams.
```

### 4.4 docs/decisions.md -- append to "## Decisions"
```
- D18 - Renderer registry - 2026-10-18 - Reports are registered renderers over the same document; HTML mirrors Markdown section for section and is tested for parity.
- D19 - HTML safety - 2026-10-18 - All document text is HTML-escaped and ASCII-encoded; only http(s) source URLs become links; the page has no script, no external resource and no event attribute.
- D20 - Line endings - 2026-10-18 - Text data files (json, jsonl, txt, html, css, svg, tmpl) are LF in the repository on every OS (found when a Windows checkout broke a byte-exact fixture test).
```
append to "## Validation records"
```
- 2026-10-18 - P1 accepted at 903f20f after independent re-run; one test failed only on a Windows checkout (CRLF in fixtures), fixed by D20.
```
append to "## Baselines"
```
- 2026-10-18 - P1 cloud build cost about 4 USD of cloud credit (whole-dollar display), no plan-limit change.
```

## 5. Build and verify (Bash)
1. Canary 0.5; `git switch -c p2-html`.
2. Apply section 2, then section 3; `python3 scripts/dd.py schema-doc > references/schema.md`.
3. `python3 -m pytest -q` (basetemp now under .scratch) until all pass; paste the tail.
4. ast check (feature_version 3.11) over scripts lib tests: OK.
5. Scans (must print nothing): the three P1 grep scans on `scripts lib`; ASCII scan on `scripts lib tests references SKILL.md docs CLAUDE.md` (assets excluded: the vendored CSS may contain non-ASCII); `grep -rnE "url\(|@import" assets/report.css`.
6. Size: print the byte size of `tests/golden/acme.report.html` and of the vendored CSS.
7. `git add --renormalize .`; `git status`; commit (message file in .scratch/misc/): `feat: P2 HTML report with vendored Lism CSS; C1-C5 fixes (v0.2.0)`; `git show --stat HEAD`; `git push -u origin p2-html`; `git ls-remote origin p2-html`; `git status --porcelain` empty.

## 6. Done criteria
- [ ] All tests pass, including 3.6 #1-#10.
- [ ] Scans empty; ast OK.
- [ ] Only 0.4 files changed; render_md.py, ledger.py, directives.py, review.py, dd.py untouched.
- [ ] Goldens changed only as allowed by 3.5, with diffs shown.
- [ ] VERBATIM greps: `self-contained HTML report (flow diagrams in a later`, `It mirrors the Markdown`, `D20 - Line endings`.
- [ ] Branch p2-html pushed; ls-remote hash equals HEAD.

## 7. Return contract
- **A** files table with line counts; Lism version, integrity, sha256 and which file was vendored; the full `assets/report.css`; `assets/report.html.tmpl`; the `<body>` part of the golden HTML up to and including section 3; diffs of any changed golden/fixture.
- **B** pytest tail; ast output; sizes; test 3.6 #3 output snippet (escaped forms).
- **C** branch, full HEAD hash, ls-remote output, `git show --stat HEAD`, scan outputs (empty), `git status --porcelain` (empty), "files outside 0.4: NONE".
- **D** anomalies (Benign / Needs decision / Not covered), including every interpretation you chose.
