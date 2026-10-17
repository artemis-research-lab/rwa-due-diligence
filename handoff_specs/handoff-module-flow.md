# handoff-module-flow -- rwa-due-diligence P3: fund-flow diagrams (D2 v0.9.0 + ELK) + carry-over C6-C7

Run as (CC **cloud** session, environment `web3-readonly`, repo `artemis-research-lab/rwa-due-diligence`):
"build the module in handoff_specs/handoff-module-flow.md"

## 0. Persistent context
- Base: `main` at `2320c9a0c192070780c02e59ccb8e89ba54a4c11` (v0.2.0, accepted). Target: v0.3.0.
- Execution: cloud (Linux, Bash). Run-time target: Claude Code Local on Windows, Python >= 3.11, OS-neutral code.
- Branch: push the **session branch** you are assigned (do not create another branch); report its name in Block C. Acceptance is anchored on the commit hash.
- D1-D20 apply. This module implements D11 and D12.

### 0.2 Verified shared contracts (actual code at the base commit)
```
lib/runstate.py
  RENDERERS = [("report.md", render_md.render), ("report.html", render_html.render)]   # fn(doc, rounds) -> str
  render_draft(root, slug): writes .scratch/draft/<slug>.<suffix> per renderer; finalize(root, slug, clock): writes outputs, returns dict
  Project.write_text / write_bytes / safe(path) (raises ContractError outside <root>/<slug>)
lib/render_html.py
  ASSETS = <skill root>/assets ; render(doc, rounds=()) -> str
  _flows(r): global nodes table, then per product: <h3>, '<figure class="dd-flow" id="flow-<Pn>"></figure>' (empty placeholder), edges table
lib/render_md.py
  render(doc, rounds=()) -> str ; section "6. Fund flows": nodes table, then per product "### <product>" + edges table
lib/schema.py
  SKILL_VERSION = "0.1.0"   (line 7)
lib/textutil.py: html_text, html_url, md_text, id_key
tests: golden acme.report.md / acme.review.md / acme.report.html; 110 tests pass at base.
```

### 0.4 File scope (HARD)
```
[NEW]  lib/flow.py                         D2 source builder + renderer wrapper (only module allowed to use subprocess)
[NEW]  tests/unit/test_flow.py
[NEW]  tests/golden/acme.flow-P1.d2, tests/golden/acme.flow-P2.d2          D2 sources (always tested)
[NEW]  tests/golden/acme.flow-P1.svg, tests/golden/acme.flow-P2.svg        rendered by d2 v0.9.0
[EDIT] lib/runstate.py      figures pipeline (3.4), SVG outputs, dependency error
[EDIT] lib/render_md.py     signature + image link per product (3.5)
[EDIT] lib/render_html.py   signature + inline SVG in the figure (3.5); C6 nothing else
[EDIT] lib/schema.py        SKILL_VERSION = "0.3.0" (C7); nothing else
[EDIT] scripts/dd.py        exit code 4 for a missing/wrong d2 (3.4); nothing else
[EDIT] assets/report.css    C6 + .dd-flow figure styles
[EDIT] tests/golden/acme.report.md, tests/golden/acme.report.html  regenerated ONLY for the changes of this spec; show full diffs
[EDIT] tests/unit/test_render_md.py, test_render_html.py, test_cli.py, test_runstate.py   new cases
[EDIT] references/schema.md (only if regenerated output changes), references/runtime.md, references/third-party.md, SKILL.md, docs/architecture.md, docs/decisions.md   (section 4)
[REUSE -- DO NOT TOUCH] tools/**, lib/ledger.py, lib/directives.py, lib/review.py, lib/claims.py, lib/validate.py, lib/textutil.py, assets/lism-css-1.0.1.min.css, assets/report.html.tmpl, tests/fixtures/**, .gitattributes, pytest.ini, CLAUDE.md, handoff_specs/**
```

### 0.5 Canary
`ls -la | head -20`; `git status --porcelain` empty; `git diff --stat 2320c9a HEAD` lists nothing or only `handoff_specs/handoff-module-flow.md`. Otherwise STOP.

### 0.6 Install probe (do this before writing any code)
Download into `.scratch/build/d2/` (never commit it):
`https://github.com/terrastruct/d2/releases/download/v0.9.0/d2-v0.9.0-linux-amd64.tar.gz`
Expected sha256 of the tarball: `5669ddc46b99e942cc96078f4a4e36d5e62103348f4c05179ede27802fdd87a9`. Mismatch -> STOP. If the download is refused by the network policy, STOP and report the exact error (this module will then be built in a Local session). After extraction, `d2 --version` must print `v0.9.0`. Add the binary directory to PATH for this session only. Also report whether this d2 build performs any network access during a render (run one render with networking unavailable if you can, or grep the binary's `--help` and docs for an update check and how to disable it).

## 1. Motivation
D11/D12: each product's fund flow is drawn as a static SVG generated deterministically from `flows`, with three lanes (offchain, boundary, onchain), so curators see who holds money, where it changes rail and which legs are unverified. Probe-1 showed D2 v0.9.0 + ELK output is byte-identical on Linux and Windows; the design session's tests on real data showed lane containers without grid give orthogonal, readable routing.

## 2. Carry-over
- **C6** report.css: the first column of every `.dd-table` (`td:first-child, th:first-child`) gets `white-space: nowrap`; `.dd-meta__row dd` uses `overflow-wrap: break-word` instead of `anywhere`. Regenerate the HTML golden for this.
- **C7** `schema.SKILL_VERSION = "0.3.0"`. Rule for all later specs: each phase spec states the version it sets. The acme fixture keeps its own `skill_version` value (it is data).

## 3. Flow diagrams

### 3.1 lib/flow.py -- D2 source builder (pure, no I/O)
`build_d2(doc, product_id) -> str`. Deterministic; same input -> same bytes on every OS. Rules:
1. Edges = `doc.flows.edges` whose `products` contains product_id, in document order. Nodes = nodes referenced by those edges, ordered by id (`id_key`).
2. Header, exactly:
```
direction: down
vars: {
  d2-config: {
    layout-engine: elk
    theme-id: 0
  }
}
```
3. Lanes in fixed order offchain, boundary, onchain; a lane is emitted only if it has at least one node. Lane block: `<lane>: "<Off-chain|Boundary|On-chain>" {` then `  direction: right`, `  style.fill: "#f8fafc"`, `  style.stroke: "#cbd5e1"`, `  style.font-size: 14`, then the nodes, then `}`.
4. Node line: `  <node id>: "<label>" {<shape>; style.font-size: 13; style.fill: "#ffffff"}` with shapes: investor `shape: person`; entity `shape: rectangle`; contract, pool, wallet `shape: rectangle; style.border-radius: 8`; multisig `shape: rectangle; style.border-radius: 8; style.double-border: true`; bank_account `shape: cylinder`; asset `shape: hexagon`.
5. Edge line: `<lane>.<from> -> <lane>.<to>: "<label>" {style.stroke: "<colour>"; style.font-size: 12<dash><opacity>}`. Colours/dash by kind: subscription #2563eb; redemption #2563eb dash 5; yield #16a34a; fee #6b7280 dash 2; custody #9333ea; conversion #0891b2 dash 3; collateral #b91c1c dash 4. Claim status: label suffix ` [V]`/` [S]`/` [I]`/` [N]` (`[N?]` when not_found without evidence); inferred edges add `; style.opacity: 0.7`; not_found edges add `; style.opacity: 0.5`.
6. **D2 escaping (security-relevant):** every label (node label, edge label, lane title) is reduced to the character set `[A-Za-z0-9 .,:;()/&+%@'_=-]`: any other character becomes a space, runs of spaces collapse to one, trim, clip to the field limit (40), then wrap in double quotes. Node ids come only from schema-validated ids (`n<k>`). Nothing else from the document enters the D2 source. Test with labels containing `"`, `\`, `}`, `{`, `#`, `$`, `|`, `<`, `>`, a newline and non-ASCII.
7. File ends with exactly one newline; LF only.

### 3.2 lib/flow.py -- renderer wrapper
- `D2_VERSION = "v0.9.0"`; `find_d2() -> str|None` uses `shutil.which("d2")` only.
- `check_d2(path) -> None`: run `[path, "--version"]`; output (stripped) must equal `v0.9.0`, else raise `DependencyError("d2 v0.9.0 required, found <x>")`.
- `render_svg(d2_source, d2_path) -> str`: `subprocess.run([d2_path, "--layout=elk", "--theme=0", "--dark-theme=-1", "--pad=24", "--scale=-1", "--center=false", "--sketch=false", "--bundle=true", "--timeout=60", "--stdout-format=svg", "-", "-"], input=<utf-8 bytes>, capture_output=True, timeout=90, check=False, shell=False)`. Non-zero exit -> `RenderError` with the first 500 chars of stderr. Explicit flags are mandatory because d2 also reads `D2_*` environment variables; flags must make the output independent of them (add a test that sets `D2_LAYOUT=dagre` and `D2_THEME=200` in the child env and still gets the golden bytes).
- `sanitize_svg(svg) -> str`: strip a leading `<?xml ...?>` declaration; then assert the SVG contains no `<script`, no `<foreignObject`, no ` on[a-z]+=` attribute inside tags, no `href=`/`xlink:href=` with a value starting with `http`, `//` or `javascript:`, no `@import`; violation -> `RenderError`. Return the text with LF line endings.
- `render_all(doc, d2_path) -> dict[product_id -> svg]` for every product, in id order.
- No other subprocess use anywhere in lib/ or scripts/ (scan in 5).

### 3.3 Outputs
For each product, `<slug>.flow-<Pn>.svg` is written to the project directory at finalize (draft render: `.scratch/draft/`). It is included in `outputs` (order: dd.json, report.md, report.html, then flow SVGs by product id).

### 3.4 Pipeline (lib/runstate.py)
- Renderer signature becomes `fn(doc, rounds, figures) -> str` where `figures` maps product id -> sanitized SVG text (may be empty dict).
- `render_draft`: if `find_d2()` is None or `check_d2` fails, render with `figures = {}` and add `"warnings": ["d2 v0.9.0 not found: diagrams omitted"]` to its result; otherwise render figures.
- `finalize`: d2 is mandatory: missing or wrong version -> `DependencyError`, which `scripts/dd.py` maps to exit code **4** with the message; nothing is written. The state stays ready_to_finalize.
- Path safety unchanged: all files through Project.

### 3.5 Report integration
- HTML: the existing figure becomes `<figure class="dd-flow" id="flow-<Pn>">` + the sanitized SVG + `<figcaption>Fund flow <Pn>: lanes off-chain / boundary / on-chain; marker after each label = claim status</figcaption></figure>`; when figures lacks the product, keep the empty figure exactly as now (so the empty-figure CSS rule still hides it).
- report.css: `.dd-flow svg { width: 100%; height: auto; max-height: 80vh; }`, figcaption small and muted; print: `.dd-flow { break-inside: avoid; }`.
- MD: under each product heading in section 6, before the edges table, when the product has a figure: `![Fund flow <Pn>](<slug>.flow-<Pn>.svg)` (relative link, slug from run.slug), followed by a blank line. No line when there is no figure.
- Parity test (P2 #6) must still pass.

### 3.6 Tests (tests/unit/test_flow.py + updates)
1. D2 source golden: `build_d2(acme, "P1")` / `"P2"` equal `tests/golden/acme.flow-P1.d2` / `-P2.d2` byte for byte (runs everywhere, no d2 needed).
2. Escaping: hostile labels (3.1 rule 6) produce only allowed characters inside quotes; the D2 source compiles (when d2 present).
3. Lanes: a product whose nodes are only on-chain emits only the onchain lane; lane order is fixed.
4. SVG golden: with d2 present, `render_svg(build_d2(acme, Pn))` after sanitize equals `tests/golden/acme.flow-Pn.svg`. Mark with `@pytest.mark.d2`; register the marker in a module-level `pytestmark` or via `pytest.importorskip`-style skip **only when d2 is absent**; Block B must show these tests ran, not skipped.
5. Env independence: same as 4 with `D2_LAYOUT=dagre`, `D2_THEME=200` in the child environment (pass `env` to the wrapper through a test-only keyword argument defaulting to None).
6. Sanitizer: SVGs with `<script>`, `onload=`, `<foreignObject>`, `href="https://x"` are rejected.
7. Version check: a fake executable path that prints `v0.8.0` -> DependencyError (create a tiny Python script and invoke it via `sys.executable`; do not rely on shell scripts).
8. Pipeline: finalize without d2 (simulate with find_d2 patched to None) -> exit 4 from the CLI, no output files, phase unchanged; draft render without d2 returns the warning and an HTML with empty figures; finalize with d2 writes the SVG files and lists them in outputs.
9. HTML golden regenerated (C6 + figures); MD golden regenerated (image links); review golden unchanged. Show diffs.
10. All P1/P2 tests still pass.

## 4. VERBATIM blocks

### 4.1 SKILL.md
(a) In the description replace `a self-contained HTML report (flow diagrams in a later` / `version)` by `a self-contained HTML report with fund-flow diagrams` / `(one per product)` keeping the original line structure.
(b) Insert after the "## Setup (once)" paragraph:
```
Install the diagram renderer d2, version v0.9.0 exactly (Windows: `winget install --id Terrastruct.D2 -e --version 0.9.0`),
and check with `d2 --version`. Without it, draft renders omit diagrams and finalize stops with exit code 4.
```
(c) In step 5 replace `The outputs are <slug>.dd.json, <slug>.report.md and <slug>.report.html.` by
```
   The outputs are <slug>.dd.json, <slug>.report.md, <slug>.report.html and one <slug>.flow-<product>.svg per product.
```

### 4.2 references/runtime.md
In "## Constraints" replace the first bullet by:
```
- Python 3.11 or newer, standard library only; the d2 binary v0.9.0 must be on PATH for diagrams (finalize requires it).
```
Append to "## Output contract":
```
- <slug>.flow-<product>.svg: one per product, generated from dd.json flows by d2 v0.9.0 with the ELK layout and fixed
  flags; lanes off-chain, boundary, on-chain; edge colour = flow kind, label suffix = claim status. The same SVG is
  embedded in the HTML report and linked from the Markdown report.
```

### 4.3 references/third-party.md -- append
```
## d2
- Name: d2 (Terrastruct), version v0.9.0, MPL-2.0. Not vendored; installed separately and invoked as a subprocess.
- Linux release used in cloud builds: d2-v0.9.0-linux-amd64.tar.gz, sha256 5669ddc46b99e942cc96078f4a4e36d5e62103348f4c05179ede27802fdd87a9.
- Windows: winget package Terrastruct.D2, version 0.9.0.
- Output of v0.9.0 with the ELK layout was verified byte-identical on Linux and Windows (probe-1, 2026-10-17).
```

### 4.4 docs/architecture.md
Under "## Modules" add after "### Reports":
```
### Flow diagrams
- Responsibility: Turn each product's fund flows into a diagram with fixed lanes and styles.
- Input: The flows section of a valid DD document.
- Output: One diagram per product, embedded in or linked from the reports.
- Depends on: Schema.
```
In "### Reports" set `- Depends on: Schema, Flow diagrams.` In "## Known Limits" replace the first bullet by `- v0.3 has no research automation.` and add `- Diagrams need the external d2 binary at the pinned version; without it only draft reports can be produced.`

### 4.5 docs/decisions.md -- append to Decisions
```
- D21 - Diagram pipeline - 2026-10-18 - D2 source is built only from schema ids and a restricted label alphabet; d2 v0.9.0 runs as a subprocess with explicit flags (ELK, theme 0) so environment variables cannot change output; the SVG is sanitised before embedding.
- D22 - Version per phase - 2026-10-18 - Every phase spec sets SKILL_VERSION explicitly (v0.3.0 for P3).
- D23 - Cloud branches - 2026-10-18 - Cloud sessions push only their assigned session branch; specs do not name branches and acceptance is anchored on the commit hash.
```
append to Baselines:
```
- 2026-10-18 - P2 cloud build cost about 3 USD of cloud credit.
```

## 5. Build and verify (Bash)
1. Canary 0.5, install probe 0.6.
2. Implement 2-4. If `references/schema.md` changes when regenerated, commit it; otherwise leave it.
3. `python3 -m pytest -q -rs` (shows skip reasons) until all pass and no d2 test is skipped; paste the tail including the `-rs` summary.
4. ast check (3.11) on scripts lib tests: OK.
5. Scans (must print nothing): P1 forbidden scan on scripts lib; `grep -rnE "^\s*(import|from) (urllib|http|socket|requests|httpx|ssl)\b" scripts lib`; `grep -rln "subprocess" scripts lib | grep -v '^lib/flow.py$'`; `grep -rnE "shell\s*=\s*True" scripts lib`; `grep -rnE "os\.environ|getenv" scripts lib`; ASCII scan as in P2.
6. Determinism: render both SVGs twice; identical. Print sizes of the two SVG goldens and the HTML golden.
7. If a headless browser is available in the session, screenshot the HTML golden's section 6 and describe it in one paragraph (lanes, crossings, labels readable). If not, say so.
8. Commit (message file in .scratch/misc/): `feat: P3 fund-flow diagrams with d2 v0.9.0 (v0.3.0)`; `git show --stat HEAD`; push the session branch; `git ls-remote origin <branch>`; `git status --porcelain` empty.

## 6. Done criteria
- [ ] Install probe passed (hash and version).
- [ ] All tests pass; d2 tests ran (not skipped); env-independence test passes.
- [ ] Scans empty; subprocess only in lib/flow.py; ast OK.
- [ ] Only 0.4 files changed; goldens changed only as listed, with diffs.
- [ ] VERBATIM greps: `with fund-flow diagrams`, `--version 0.9.0`, `D21 - Diagram pipeline`, `### Flow diagrams`.
- [ ] Session branch pushed; ls-remote equals HEAD.

## 7. Return contract
- **A** files table with line counts; full `lib/flow.py`; `tests/golden/acme.flow-P1.d2`; diffs of the regenerated MD and HTML goldens limited to changed hunks (SVG body may be elided after its first 5 lines); sizes.
- **B** install probe output (hash, version, network finding); pytest tail with `-rs`; ast; determinism; screenshot paragraph or "no browser".
- **C** branch, full HEAD, ls-remote, `git show --stat HEAD`, scans (empty), `git status --porcelain` (empty), "files outside 0.4: NONE".
- **D** anomalies (Benign / Needs decision / Not covered) with every interpretation you chose.
