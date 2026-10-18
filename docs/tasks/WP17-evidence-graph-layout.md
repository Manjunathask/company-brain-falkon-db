<context>
Read AGENTS.md, web/graph.js, web/app.js (functions `draw`, `evidence`, `runToolSuggestion`, `send`) and
tests/js/test_graph_cap.mjs first. Front-end only: no query, Python or CSS change. Do not touch docs/blog-submission/.

Bug seen on 18 Oct before recording the demo: in the Ask view, asking "Why was Managed Commits rejected, and what
replaced it?" (a starter chip) drew its evidence graph, "41 nodes · 40 links", as one horizontal line.
Reproduced by Claude Code in the built-in browser at 1280x800 (evidence canvas 445 x 560 px) by calling
`renderEvidence` with the `why_not` graph. The graph is a star: `Catalog-Managed Tables` has 40 links (38 people,
issue #4381, `Managed Commits`); every other node has 1.

Non-departure graphs use `{name: "breadthfirst", directed: false, roots: [...]}` (graph.js, `const layout`).
Breadthfirst draws each level of the tree as one row. Two separate causes:

1. Roots that match nothing. The Ask view passes the first tool call's parameter values as roots
   (`Object.values(params)`), and `mainNode` keeps only nodes whose key/login/path/slug equals one of them. When the
   agent's first call is `find_entity {text: "Managed Commits"}`, nothing matches, `roots` is `[]`, and Cytoscape
   treats every node as unreached and puts all of them on a single row: measured 1 row, 2,935 px wide, zoom stuck at
   the 0.3 minimum. Without the `roots` option Cytoscape roots each connected part at its best-connected node.
2. Wide levels. When the root does match (`slug: managed-commits`), the rows are 1 / 1 / 39 nodes: 2,795 px wide,
   still zoom 0.3, and it does not fit the canvas either.

The same happens to other Ask starters (direct tool calls, measured on the live graph):
- `declared_vs_actual` 49 nodes and `bus_factor` 43 nodes: no root matches, so one row of all nodes.
- `simulate_departure harperjiang` 50 nodes: levels 1 / 49. `successor` 44 nodes: widest level 20.
- Every graph over the 60-node cap whose roots match nothing (bus_factor_component, bridges, groups, drift).
- Fine today and must stay as they are: the handover graph (11 nodes) and `decision_share harperjiang` (22 nodes,
  widest level 9) are breadthfirst; the departure focus graph uses the `concentric` layout and is not touched.

Prototype in the page: breadthfirst with `circle: true` (each level on a ring instead of a row) draws the why_not star
readably (zoom 0.53, hub with its 40 spokes, Managed Commits on the ring); `cose` overlapped labels badly.

The Reset button (`.reset-graph`) runs a different layout from the one drawn: `{name: "breadthfirst"}` with no roots,
and a second copy of the departure concentric layout. For the why_not graph that reset gives rows 1 / 40.
</context>

<task>
All changes in web/graph.js unless stated. Keep it small and plain; the developer must be able to explain every line.

1. Roots. Build the root id list as today. Pass `roots` to breadthfirst only when the list is non-empty; otherwise
   leave the option out so Cytoscape picks the best-connected node of each part. Add a one-line comment saying why
   (an empty list puts every node on one row).

2. Wide levels. After Cytoscape draws a breadthfirst layout, count how many nodes share each row (nodes on one level
   have the same `position("y")`; round it). If the widest row holds more than `MAX_ROW = 10` nodes, run the same
   layout again with `circle: true`. Put the counting in a small exported helper (e.g. `widestRow(nodes)` taking a
   Cytoscape collection or any array-like of objects with `position(dim)`), so it can be tested without Cytoscape.
   Comment: breadthfirst draws each level as one row; more than MAX_ROW nodes in a row cannot be read in the panel
   (a decision with 38 participants), so draw the levels as rings.

3. Reset. Make the Reset button run exactly the layout that was drawn (including `circle: true` when chosen), then
   fit. Remove the duplicated concentric object in the reset handler; one layout object, used by both.

4. Layout choice as a pure function. Move the layout decision out of `renderEvidence` into an exported function,
   e.g. `evidenceLayout(shown, roots, mode)`, returning the concentric layout for "departure", breadthfirst (with or
   without `roots`) when there are 2+ nodes and edges, and cose otherwise, exactly as today apart from item 1.
   `renderEvidence` calls it, creates Cytoscape, applies item 2, and wires Reset to the final layout.

5. Cache busting: in web/app.js change the import to `./graph.js?v=17`, and in web/index.html load
   `/app.js?v=17` (leave style.css and people-combobox.js as they are).

6. Tests: add tests/js/test_graph_layout.mjs (same data-URL import trick as test_graph_cap.mjs) and a pytest wrapper
   next to `test_graph_cap_javascript_unit` in tests/test_api_integration.py. Cover: departure mode returns
   concentric; roots that match nothing produce a breadthfirst layout with no `roots` key; a matching slug or login
   produces `roots` with that node's id as a string; a single node or no edges gives cose; `widestRow` returns the
   largest count of equal rounded y values (e.g. ys [0, 0.2, 100, 100, 100] -> 3) and 0 for an empty list.
   Existing tests must still pass.

Do not change node styles, the 60-node cap, `capConnectedGraph`, minZoom/maxZoom, or anything in the Leave view
other than what Reset now does.
</task>

<checks>
Run `.venv/Scripts/python -m pytest -q` and `node tests/js/test_graph_layout.mjs`. You have no browser; the reviewer
will check the why_not, declared_vs_actual, handover and departure graphs live at 1280x800.
</checks>

<report>
Write what you changed (files, functions), the exact MAX_ROW rule, and test results to
docs/tasks/WP17-evidence-graph-layout.report.md. Do not edit README.md, docs/PROGRESS.md or docs/blog-submission/.
Do not commit.
</report>
