# handoff-probe-flow -- rwa-due-diligence: fund-flow layout on real data

Route: CHAT (OS-neutral; pinned d2 v0.9.0 binary; inputs are the three accepted final records; no network, no secrets).
Run by CChat via `run probe flow`. Result decides whether a patch to lib/flow.py is specified.

## 1. Purpose
The accepted reports (usd-ai v2, huma v1, hastra v1; 8 product diagrams) show long cross-lane edges routed around
the lane containers. Find a layout that shortens them without giving up the D21 contract: deterministic output,
three lanes (off-chain, boundary, on-chain) still visible, same edge styles and labels, sanitizer unchanged.

## 2. Inputs
`<root>/<slug>/<slug>.dd.json` for usd-ai, huma, hastra (read-only copies), lib/flow.py at v0.4.2 (`124f592`).

## 3. Variants (only the D2 header, lane blocks and d2 flags change; edges and labels are identical)
- V0 baseline: ELK, top-level direction down, lanes as containers with internal direction right.
- V1 swim columns: ELK, top-level direction right, lanes internal direction down.
- V2 V0 plus ELK spacing: --elk-nodeNodeBetweenLayers=40 --elk-edgeNodeBetweenLayers=20 --elk-padding=[top=30,left=30,bottom=30,right=30].
- V3 V1 plus the V2 spacing.
- V4 dagre engine with V0 structure.
- V5 no lane containers: lane shown by node fill colour and a 3-row legend; ELK, direction right.

## 4. Metrics per product diagram
SVG width, height, area; edge count; total and maximum edge path length (from the SVG path d); number of path
segments (bends); edges whose path leaves the bounding box of the union of their two endpoint lanes (V0-V4 only);
render time; byte-identical on a second render (Y/N). Plus a PNG screenshot of each variant for visual review.

## 5. Return contract
- P1 table: product | variant | width x height | area | total edge length | max edge length | bends | out-of-lane edges | identical (Y/N).
- P2 per-variant medians across the 8 diagrams, relative to V0.
- P3 screenshots of the best two variants for the largest diagram (huma P1) and one small one.
- P4 recommendation with the exact D2 header, lane-block and flag changes, and which tests/goldens they would touch.
