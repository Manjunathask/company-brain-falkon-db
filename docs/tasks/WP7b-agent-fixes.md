<task>
You are implementing work package WP7b of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md, docs/PROGRESS.md,
docs/QUERIES.md. WP1-WP7 are done and committed. A reviewer eval ran 5 demo questions through the live agent on
Sonnet 5.5 (low and medium effort) and Opus 5.5 (medium). Fix what it found. Do not touch src/busfactor/api/ or web/
(another package, WP8, may be editing them).

Findings and fixes:
1. Latency: connecting to "localhost" costs 2.06 s per new connection on this Windows machine (IPv6 tried first;
   Docker publishes on 127.0.0.1) against 0.007 s for 127.0.0.1. Every tool, evidence and memory query opened a new
   client, so one question took 95 s; with FALKORDB_HOST=127.0.0.1 the same question took 16 s.
   - Default FALKORDB_HOST to 127.0.0.1 everywhere (db.py, whatif.py, memory.py, scripts, tests, .env.example,
     README) and explain why in one comment in db.py.
   - Reuse one FalkorDB client per process (a small cached factory in db.py: get_client(), get_graph(name)), instead
     of constructing a client per call. whatif.py and memory.py use it too.
2. simulate_departure failed with "Invalid graph operation on empty key" when two simulations ran at the same time
   (two eval processes, same login, seconds apart). After GRAPH.COPY, wait until the copy is queryable (poll EXISTS
   or a trivial ro_query, 50 ms steps, 5 s timeout, clear error if it never appears). Make the graph name collision-
   proof (add a random suffix, not only a timestamp). Add an integration test that runs two simulations concurrently
   (threads) on the fixture and both succeed and clean up.
3. decision_trace returned only paths, so the model saw internal node ids (e.g. 6922) instead of decision names.
   10_decision_trace.cypher must also return explicit columns: file, commitSha, commitTs, prNumber, prTitle,
   decisionSlug, decisionTitle, decisionStatus, confidence, via, issueNumber. Check every other tool for the same
   problem (rows that contain only nodes, relationships or paths) and give them readable columns.
4. Noise: `(test-resources)` components (fixtures, parquet/crc data) show up as ORPHANED in departure answers.
   Exclude components whose name ends with "/(test-resources)" from 05b, 06 and 06b by default, with a parameter
   includeTestResources (default false) so it stays explainable.
5. departure_impact returned 48 rows and the loop truncated at 40, hiding some components. Add an optional
   componentPrefix parameter (e.g. "spark/v2") to 06 and 06b, and order 06 so that ORPHANED and AT RISK rows with
   the most of their commits come first.
6. Parallel tools: the model often requests several tools in one turn. Execute the tool calls of one turn
   concurrently (ThreadPoolExecutor, max 6 workers), keep the tool_result order equal to the tool_use order, and keep
   one tool_result message per turn.
8. find_entity misses partial logins: searching "murali" returns no person because 13_find_entity matches only an
   exact login or a substring of p.name. Also match `toLower(p.login) CONTAINS toLower(text)`, and rank exact login
   matches first (score 2.0), then login prefix, then contains.
9. Do not edit README.md or docs/PROGRESS.md in this package (another package runs in parallel); put the README
   changes you would have made (127.0.0.1 note) in your report instead.
7. Default effort stays "medium" (the eval showed low effort gave up on an ambiguous question that medium solved).
   Default model stays claude-sonnet-5-5.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, data/delta, src/busfactor/api/
or web/. Do not run git commit. No live LLM calls.
</action_safety>

<verification_loop>
pytest including integration tests must pass. Show the timing of `python -m busfactor.tools departure_impact --login
scottsand-db` before and after fix 1, the concurrent-simulation test passing, and decision_trace rows for
kernel/kernel-api/src/main/java/io/delta/kernel/internal/icebergcompat/IcebergCompatMetadataValidatorAndUpdater.java.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; the timings; the decision_trace rows; anything uncertain.
</compact_output_contract>
