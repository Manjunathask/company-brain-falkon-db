<task>
You are implementing WP11a, the backend half of the UX revamp of "Bus Factor". Read AGENTS.md, docs/PROGRESS.md,
docs/QUERIES.md and the approved plan docs/tasks/WP11-ux-revamp-plan.md (and its review
docs/tasks/WP11-plan-review-codex-astra.md). Use `.venv/Scripts/python` for everything; FalkorDB is reachable at
127.0.0.1:6379 with the live `delta` graph.

A second Codex session (WP11b) is changing web/ and tests/test_api_integration.py at the same time. Touch ONLY:
src/busfactor/** , queries/** , docs/QUERIES.md and a NEW test file tests/test_api_revamp.py. Do not edit web/,
tests/test_api_integration.py, README.md or docs/PROGRESS.md (the reviewer updates the last two).

JSON contract the frontend codes against (keep these names exactly):
1. GET /api/summary -> {busFactorOne, componentsReported, windowDays, minCommits, minTotal,
   examples:[{component, topExpert, total}] (top 3 bus-factor-1 components by total commits), snapshotDate,
   dataWindow}. Reuse tools.bus_factor_component() (query 05b) with the tool defaults; one query. snapshotDate from
   data/snapshot/manifest.json exported_at (date only) when present, else today; dataWindow is a short sentence like
   "2 years loaded; risk uses the last 12 months and at least 2 commits".
   Live today this gives busFactorOne=42, componentsReported=87 (assert with a tolerance, not exact, in tests that hit
   the live graph; the fixture tests assert exact values).
2. GET /api/people?q=&limit=10 -> {people:[{login, name, recentCommits, lastSeen}]}. New
   queries/17_people_search.cypher: Active, non-bot people; recentCommits = non-bulk authored commits since $since;
   empty q -> top by recentCommits; non-empty q (case-insensitive) -> login or name STARTS WITH first, then CONTAINS,
   each group ranked by recentCommits desc, then login. limit 1..25. Read-only (ro_query).
3. GET /api/suggestions -> {suggestions:[{id, question, tool?, params?}]}: 4 named starter questions from live data:
   the top maintainer from 17 ("What does the project lose if <name> (@login) leaves?", tool departure -> the UI can run
   it without the LLM), the busiest bus-factor-1 component with its top expert ("Who could take over <component> if
   <topExpert> left?", tool successor with params), the superseded decision via the SUPERSEDED_BY edge ("Why was
   <old title> rejected, and what replaced it?", tool why_not with slug), and "Where do the declared CODEOWNERS differ
   from the people doing the work?" (tool declared_vs_actual). `tool`/`params` let the UI answer without an API key.
4. POST /api/ask response gains `followups: [string]` (max 4, deduplicated) built by a new
   src/busfactor/agent/followups.py: one template table keyed by tool name, fed with the params and the ROWS of
   successful tool calls inside the loop (rows exist there, see loop.py around the tool execution; the returned
   tool_calls only carry row_count). Only use entities present in those rows/params, never parse the answer prose.
   Examples: departure_impact for X with an ORPHANED/AT RISK component C -> "Who could take over C if X left?";
   decision_share rows -> "Who else worked on <decision>?"; simulate_departure with cutOff -> "Who would lose their link
   to the main collaboration network if X left?"; decision_trace with a decision -> "Who took part in <decision title>?";
   why_not -> "Which files changed since <new decision title> was accepted?" only when drift data supports it. Each is
   a complete question with names filled in. Unit-test the table per tool.
5. GET /api/departure/{login} gains `summary: {name, orphaned, atRisk, orphanedFiles, cutOff, mainGroupBefore,
   mainGroupAfter, bridgeRank}` (counts from the existing tool results; name from the Person node, fallback login) and
   returns 404 {"detail": "No active person with login '<x>' in the graph."} for an unknown login (check before running
   the simulation).
6. Anonymous visitors: memory accepts users matching `v_[0-9a-f]{32}` in addition to the existing login pattern
   (src/busfactor/agent/memory.py memory_graph_name). New DELETE /api/memory/{user} (only for v_ ids): deletes
   mem_<user> and the team-memory observations whose agent is chat:<user>; returns {deleted: true, teamClaimsRemoved: n}.
   Make sure an /api/ask that finishes after a delete does not recreate the history (check a small in-process
   "deleted ids" set, documented as best effort).
7. Plain-English tool labels: one table TOOL_LABELS in tools.py (e.g. simulate_departure -> "Simulated the departure on
   a copy of the graph"); include `label` in each tool_calls entry of AgentAnswer and in /api/tools.
8. Departure people search must no longer need find_entity; keep find_entity for the agent.

Tests in tests/test_api_revamp.py (FastAPI TestClient on the fixture graph as existing tests do, plus a few live-graph
checks marked integration): summary shape and counts; people ranking and prefix/name match (e.g. on the fixture, and
live: q="m" returns murali-db first); suggestions are named and carry tool/params; followups per tool reference only
entities from rows; unknown person -> 404 message; visitor-id validation (bad ids -> 400); delete removes only that
visitor's graph and claims; labels present.
</task>

<action_safety>
Stay inside the files listed above. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, data/delta or data/snapshot. Do
not run git commit. No live LLM calls. Every new query is its own .cypher file with a header, and gets a
docs/QUERIES.md entry.
</action_safety>

<verification_loop>
`.venv/Scripts/python -m pytest -q` must pass (it will also run WP11b's frontend tests; if one of THEIR tests fails
because of their in-progress work, report it, do not edit their files). Show live outputs of /api/summary,
/api/people?q=m&limit=5, /api/suggestions via TestClient against the live graph.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; the three live outputs; any contract change you had to make (should be none).
</compact_output_contract>
