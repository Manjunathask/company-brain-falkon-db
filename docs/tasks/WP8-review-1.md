<review>
Reviewer (Claude Code) tested the UI in a browser at 1280x800 against the live graph (departure for murali-db).
The API works and the page loads. Fix the items below. Another package (WP7b) is editing the backend in parallel:
touch only src/busfactor/api/, web/ and tests/test_api_integration.py. Do not edit README.md, docs/PROGRESS.md,
src/busfactor/tools.py, db.py, whatif.py, agent/ or queries/; if you need a backend change, describe it in your report.
</review>

<fixes>
1. Departure panel renders empty sections although the API returns data:
   - "People cut off from the main group" shows the count 3 but no names (simulation.rows[0].cutOff has
     chenwang-databricks, dillitz, ni-mi).
   - "Orphaned files by component" is empty (files.rows has 18 rows: component, orphanedFiles, theirFiles,
     examplePaths).
   - "Decisions they carry · who to ask" is empty (decision_share.rows has 1 row with decision, theirPRs, totalPRs,
     share, otherOpeners).
   - Successor lines read "undefined component commits": the API field is theirCommits, the UI reads componentCommits.
   Fix the field access, and add a TestClient + small JS-free test that the departure JSON has the fields app.js
   reads (list them in one constant in app.js and assert the same names in the test).
2. Component exposure lists all 57 rows. Show ORPHANED and AT RISK rows (with "their commits" and the remaining
   expert's login for AT RISK), then a single collapsed line "+ 41 covered components" that expands on click.
   Fix plurals ("1 expert left", "2 experts left").
3. The evidence graph is an unreadable hairball (199 nodes, 560 edges). For the departure view, build a focused graph
   in api/app.py from the tool results already returned (no new Cypher needed): the departing person at the centre;
   their ORPHANED and AT RISK components (max 10, by their commits); for AT RISK, the one remaining expert; the
   cut-off people with their WORKS_WITH edge to the person; the decisions from decision_share with the other openers;
   the successor. Return it as `focus_graph` (keep the full `graph` too) and draw focus_graph by default with a
   "show full evidence" toggle. Use a layout that keeps the departing person central (concentric or breadthfirst
   rooted at the person); label nodes with login/name, not ids; colour by risk (ORPHANED red, AT RISK amber).
   For the chat view, cap drawn nodes at 60 (prefer nodes on the paths of the last tool calls) with the same toggle.
4. The "Best successor" uses top_orphaned_component, which is currently the first ORPHANED row (spark-unified/sql,
   one shared file). Choose the ORPHANED or AT RISK component with the most of the person's commits instead, and
   say which component it is in the heading.
5. Graph legend and node details: clicking a node shows its properties; make sure File nodes show the path and
   Component nodes their name. Keep it readable at 390px wide (graph below the panel).
</fixes>

<verification_loop>
pytest must pass. Start the server and fetch /api/departure/murali-db; include the focus_graph node and edge counts
and the chosen successor component.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; focus_graph counts; any backend change you need (described, not made).
</compact_output_contract>
