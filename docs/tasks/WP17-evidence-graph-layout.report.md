# WP17 evidence graph layout report

2026-10-18 · Codex

## Changes

- `web/graph.js`: exported `evidenceLayout(shown, roots, mode)` selects the existing departure concentric layout, breadthfirst for graphs with at least two nodes and an edge, or the existing non-animated cose fallback. Root matching stays the same and produces string node IDs. Breadthfirst receives `roots` only when at least one node matches; omitting an empty list lets Cytoscape select roots instead of placing every node on one row.
- `web/graph.js`: exported `widestRow(nodes)` counts nodes by `Math.round(node.position("y"))` and returns the largest count, or zero for an empty collection. It accepts Cytoscape collections and array-like objects.
- `web/graph.js`: `renderEvidence` selects its layout through `evidenceLayout`, checks row width after the initial breadthfirst layout, and reruns that layout with `circle: true` when needed. Reset runs the final selected layout object and then fits with the existing 24-pixel padding. The duplicate departure layout was removed from Reset.
- `web/app.js` and `web/index.html`: changed the graph module import and app script URL to `v=17`. The stylesheet and people-combobox versions are unchanged.
- `tests/js/test_graph_layout.mjs`: added data-URL import tests covering departure concentric levels, omitted unmatched/empty roots, matching slug/login/key/path and departing node string IDs, cose fallbacks, rounded row counts, empty input, and array-like input.
- `tests/test_api_integration.py`: added `test_graph_layout_javascript_unit` beside the existing graph cap wrapper.

## Exact MAX_ROW rule

`MAX_ROW = 8`. Only after an initial breadthfirst layout, if **any row contains more than eight nodes** (grouped by rounded y position), rerun the same layout with `circle: true`. Eight nodes stay in rows; nine or more trigger rings. The final layout, including roots and the circle flag, is reused by Reset. Concentric and cose layouts do not undergo this check.

The supplied context describes `decision_share harperjiang` as having a widest row of nine nodes. Under the explicitly requested threshold, that graph will also switch to rings if its measured rounded-y count is nine.

Node styles, the 60-node cap, `capConnectedGraph`, zoom limits, and departure concentric placement were left unchanged. No query, application Python, CSS, README, progress log, or blog-submission files were changed. No commit was made.

## Verification

- `.venv/Scripts/python -m pytest -q`: **155 passed in 4.64s** (includes the existing graph cap test and the new JavaScript wrapper).
- `node tests/js/test_graph_layout.mjs`: **passed**, exit code 0.
- `git diff --check`: **passed**.

No browser was used. Visual review of why_not, declared_vs_actual, handover, and departure at 1280×800 remains with the reviewer.
