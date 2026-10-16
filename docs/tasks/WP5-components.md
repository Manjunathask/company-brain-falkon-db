<task>
You are implementing work package WP5 of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md,
docs/PLAN.md and docs/PROGRESS.md. WP1-WP4 are done; follow their conventions (db.run_query(bare name),
header comments, PLAN numbering with letter suffixes, lower-cased logins, bots excluded from derived
edges, exact rebuild of derived edges on re-run, integration tests in tests/test_graph_integration.py).

Why (reviewer finding on the live graph): Module = first path segment is too coarse for the headline demo.
`spark` has 115 people and a bus factor of 16; if the top author leaves, every module reports COVERED.
The real risk sits inside packages such as spark/coordinatedcommits, kernel-api/replay, spark/typewidening.
Add a Component level under Module and file-level departure risk. Module stays exactly as it is.

Build:
1. src/busfactor/ingest/components.py: component_of(path) -> str, a small documented rule:
   - Source files: match `^(?P<project>.+?)/src/(main|test)/(scala|java|python|resources)/(?P<rest>.+)$`.
     Strip the longest matching package prefix from `rest` (a short explicit list, e.g.
     org/apache/spark/sql/delta, io/delta/kernel/internal, io/delta/kernel/defaults/internal,
     io/delta/kernel/defaults, io/delta/kernel, io/delta/flink, io/delta/sharing, io/delta/storage, io/delta,
     org/apache/spark/sql, io/unitycatalog). The component is `<project>/<first remaining directory>`;
     a file directly in the package root goes to `<project>/(core)`. Main and test code of the same package
     map to the same component on purpose (knowing the tests is knowing the code).
   - Other files: the first two path segments (`docs/source`, `.github/workflows`, `connectors/docs`);
     root-level files -> `root`.
   Reviewer's sample over the last two years: about 194 source components; the largest are spark/(core),
   spark/v2/spark, kernel/kernel-api/(core), kernel/kernel-defaults/(core), spark/amt, spark/commands,
   spark/sources, spark/coordinatedcommits, kernel/kernel-api/util. Print the top 40 components by touches
   and any path the rule could not place, from `python -m busfactor.ingest.components`.
   Unit-test component_of with real-looking paths (main vs test, package root, kernel-defaults internal,
   non-source, root file).
2. Graph: `(:File)-[:IN_COMPONENT]->(c:Component {name})-[:IN_MODULE]->(:Module)`. Index Component.name.
   Add the component to each file row in load.py and a query file 01f_load_components.cypher (or extend
   01_load_commits if that is clearer; say which and why). Re-running must be safe.
3. Derive: 03c_derive_knows_component.cypher -> `(p)-[:KNOWS {commits, lastTouched}]->(c:Component)`
   (same relationship type as for modules, different target label; count DISTINCT commits; no bots;
   exact rebuild). Run it from derive.py after 03_derive_knows.
4. Agent tool queries (these are PLAN.md queries 5 and 6, now per component; the agent is built later,
   just write and test the query files):
   - 05_bus_factor.cypher: PLAN.md query 5, generalised with `$level` in ['Module','Component'] is NOT
     possible in Cypher labels, so write two files: 05_bus_factor.cypher (Module, as in PLAN) and
     05b_bus_factor_component.cypher (Component). Both take $since and $minCommits, and also return
     `people` and `total` so the answer can say "N of M commits".
   - 06_departure_impact.cypher: PLAN.md query 6 per Component, plus 06b_departure_files.cypher: for
     `$login`, the files they touched since $since where no other Active, non-bot person touched the same
     file since $since ("orphaned files"), grouped by component with counts, ordered by count. Return
     component, orphanedFiles, theirFiles, and up to 5 example paths.
   - scripts/try_queries.py: runs 05, 05b, 06, 06b for a given --login against the live graph and prints
     readable tables (this is for the reviewer and the demo script, not the agent).
5. Integration tests: component loading, KNOWS to Component, 05b busFactor on a tiny fixture (one author with
   3 of 4 commits -> bus factor 1), 06b orphaned files (a file only the departing person touched is orphaned;
   a file also touched by an Active other is not; a bot's touch does not count as coverage).
6. Append one line to docs/PROGRESS.md. Add the Component level to the README graph-model section (create the
   section if missing) in two sentences: what a Component is and why it exists.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta.
Do not run git commit. Plain readable code; every query file has a header (what it answers, parameters,
why this shape).
</action_safety>

<verification_loop>
FalkorDB is running and reachable from your sandbox at localhost:6379. `.venv/Scripts/python -m pytest -q`
must pass including the integration tests. Run `python -m busfactor.ingest.components` and include its
summary. Then rebuild the live `delta` graph with the full pipeline (load all -> link_decisions -> derive)
and run `python scripts/try_queries.py --login huan233usc` and `--login scottsand-db`; include the output.
The headline check: for at least one of them, some components must come out AT RISK or ORPHANED, or
06b must list orphaned files. If not, say so plainly rather than tuning thresholds to force it.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; component summary (count, top 15, unplaced paths); decisions for the
reviewer; anything uncertain.
</compact_output_contract>
