<task>
You are implementing work package WP6 of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md,
docs/PLAN.md ("Agent tools" queries 7-12) and docs/PROGRESS.md. WP1-WP5 are done; follow their conventions.
FalkorDB is reachable at localhost:6379 and the live `delta` graph is loaded (pipeline: load all ->
link_decisions -> derive). Hard rule 1 applies: every answer must come from a Cypher query or a FalkorDB
algorithm.

Scope: the remaining agent-tool queries and a tool registry the agent (WP7, LLM not chosen yet) will call.
No LLM code in this package.

Build:
1. Query files (header: what it answers, parameters, why this shape), adapted from PLAN.md to the current
   model (Component level, Active from any activity, IMPLEMENTS/PARTICIPATED_IN confidence, bots excluded):
   07_orphaned_decisions.cypher    PLAN 7. Add $minConfidence ('high' or 'low'): only count participation at or
                                   above it. Return decision, status, othersStillActive, whoToAsk.
   08_successor.cypher             PLAN 8, for a Component ($component) instead of a Module; rank candidates by
                                   shared recent files, tie-break by their KNOWS commits on that component; Active,
                                   non-bot only. Return successor, sharedFiles, outOf, theirCommits.
   09_bridges.cypher               PLAN 9 betweenness over :Active and WORKS_WITH.
   09b_groups.cypher               PLAN 9 WCC group count (and the size of each group).
   10_decision_trace.cypher        PLAN 10 for a file path; return the path p plus confidence and via of the
                                   IMPLEMENTS edge; prefer high-confidence links first, then most recent.
   10b_why_not.cypher              PLAN 10 "why not?" version.
   11_drift.cypher                 PLAN 11; use only high-confidence IMPLEMENTS by default ($minConfidence).
   12_declared_vs_actual.cypher    PLAN 12; Module level (CODEOWNERS is module-level).
   13_find_entity.cypher           resolve free text to graph keys: people (login or name CONTAINS, lower-cased),
                                   modules, components, decisions (title/slug), files (path ENDS WITH). Use a
                                   FalkorDB full-text index for Decision.title and PR.title if it helps (create it
                                   in 00_indexes, `CALL db.idx.fulltext.createNodeIndex`); check the procedure
                                   name/signature against the live server and say what you found.
2. What-if departure (the headline). src/busfactor/whatif.py: simulate_departure(login) uses GRAPH.COPY
   (verified to exist on our server) to copy `delta` to `whatif_<login>_<timestamp>`, removes :Active from the
   person in the copy, runs 09_bridges and 09b_groups before/after on the copy, deletes the copy in a finally
   block, and returns: groups before/after, the person's betweenness rank before, and which people end up in
   a different group from their former collaborators. Never modify the `delta` graph.
3. src/busfactor/tools.py: a plain registry. One function per tool with typed parameters and a docstring that
   doubles as the LLM tool description (bus_factor, bus_factor_component, departure_impact, departure_files,
   orphaned_decisions, successor, bridges, groups, simulate_departure, decision_trace, why_not, drift,
   declared_vs_actual, find_entity). Each returns a dict:
   {tool, params, cypher (the exact query text run; a list for simulate_departure), rows (list of dicts with
   column names), graph: {nodes: [{id, label, key, props}], edges: [{source, target, type, props}]}}.
   `graph` is the evidence subgraph for the UI: for path-returning queries, convert the returned paths; for
   table queries, build it with a small follow-up Cypher that returns the relevant nodes and relationships
   (for example departure_impact: gone -KNOWS-> component <-KNOWS- remaining experts). Keep that follow-up
   query in its own .cypher file too (suffix _graph). Default parameters ($since = now - 365 days,
   $minCommits = 2, $minTotal = 5, $minConfidence = 'low') live in one place.
   `python -m busfactor.tools <tool> --param value ...` prints rows as a table and the node/edge counts.
4. docs/QUERIES.md: one entry per .cypher file (all of them, 00 to 13): name, what it answers, parameters,
   and a 2-3 sentence plain-English explanation of how the traversal works, for the developer to explain to
   judges. Generate the list from the files but write the explanations by hand.
5. Integration tests for every tool on the tiny fixture graph (bf_test), including simulate_departure on a
   fixture where removing one person splits a group (2 groups -> 3), and a check that `delta` is unchanged.
6. Append one line to docs/PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta.
Do not run git commit. Plain readable code; no framework that hides the Cypher. Never modify the live
`delta` graph from tools (read-only queries; what-if runs only on a copy).
</action_safety>

<verification_loop>
pytest must pass including integration tests. Then run against the live graph and include output for:
`tools find_entity --text "catalog"`, `tools departure_impact --login huan233usc`,
`tools successor --login huan233usc --component kernel-spark/catalog` (or the top orphaned component),
`tools orphaned_decisions --login scottsand-db`, `tools decision_trace --path <a file under icebergcompat>`,
`tools simulate_departure --login timothyw553` (or the top betweenness person), and `tools bridges`.
Also list all graphs before and after (GRAPH.LIST) to prove no what-if copy is left behind.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; the live outputs above (trimmed); the full-text procedure you verified;
decisions for the reviewer; anything uncertain.
</compact_output_contract>
