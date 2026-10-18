# WP17 review 1 (Claude Code, 18 Oct)

Codex's diff matched the brief. Two review changes, made by Claude Code:

- `MAX_ROW` 8 -> 10. The first brief said 8, which contradicted its own "decision_share stays as it is" (widest row 9).
  Codex ran on that version and flagged the conflict in its report; the brief now says 10. Rows of 9 read fine in
  the 443 px panel (decision_share draws at zoom 0.56).
- One-line comments above `MAX_ROW`, `evidenceLayout` and `widestRow`, like the rest of graph.js.

## Live checks (built-in browser, 1280x800, `?v=wp17a`; page loaded `app.js?v=17` and `graph.js?v=17`)

Each graph drawn with `renderEvidence` in the Ask panel (canvas 443 x 558). "Before" positions were recorded with the
old graph.js on the same data and compared node by node.

| Graph | Before | After |
| --- | --- | --- |
| why_not, root matched (chip) | rows 1/1/39, 2,795 px wide, zoom 0.3 | rings, fits (383 x 371), zoom 0.51 |
| why_not, root not matched (agent) | one row of 41, 2,935 px, zoom 0.3 | rings, fits, zoom 0.54 |
| declared_vs_actual (49) | one row of 49 | rings, fits, zoom 0.35 |
| bus_factor (43) | one row of 43 | rings, fits, zoom 0.45 |
| simulate_departure (50) | rows 1/49 | rings, fits, zoom 0.54 |
| successor (44) | widest row 8 | unchanged (rows) |
| handover harperjiang + flink/inttest (11) | breadthfirst | identical node positions |
| departure focus harperjiang (20) | concentric | identical node positions |
| decision_share harperjiang (22) | breadthfirst, widest 9 | identical node positions |

End to end: clicking the starter chip "Why was Managed Commits rejected, and what replaced it?" (agent on) drew
"41 nodes · 40 links" as rings at zoom 0.51 inside the canvas. Reset restores the same layout (checked by moving a
node and pressing Reset).

pytest: 155 passed. `node tests/js/test_graph_layout.mjs` and `test_graph_cap.mjs` pass.

## Not done here (follow-ups)

- declared_vs_actual and bus_factor are networks with several parts, not trees; they now fit, but labels are small.
  `cose` drew declared_vs_actual more readably (zoom 0.51, separate parts apart) while it overlapped labels on the
  why_not star. Choosing cose for graphs with many cycles would be a separate tuning step.
- `POST /api/tools/decision_trace` returns 500: column `p` holds a raw `falkordb.path.Path` that FastAPI cannot
  serialise. Not a layout issue.
- graph.js labels any node with `props.number` as "PR #N", so issue #4381 shows as "PR #4381" in this graph.
