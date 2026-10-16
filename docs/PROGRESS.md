# Progress log

One line per finished step, newest at the bottom: date · agent · what changed · what to check.

- 2026-10-14 · Claude (chat) · Picked delta-io/delta; wrote graph model and 13 Cypher queries in `docs/PLAN.md` · Run the "Test these first" checklist in PLAN.md once data is loaded
- 2026-10-15 · Claude (chat) · Added `AGENTS.md`, `CLAUDE.md`, `docs/PLAN.md`, `docs/PROGRESS.md` · Next: Thursday's row in the schedule (Docker + loaders)
- 2026-10-16 · Codex · Added local git/RFC/CODEOWNERS ingestion, FalkorDB plumbing and load queries, CLI, README, and tests · Check parser output counts and confirm Docker volume path/persistence when Docker is available
- 2026-10-16 · Codex · Added cached GitHub GraphQL ingestion for identities, PRs, RFC issues, and reference loading with fixtures · Check API query shapes, pagination/costs, and real counts after setting GITHUB_TOKEN
- 2026-10-16 · Codex · Added WP3 derive queries and CLI, FalkorDB assumptions checker, and query contract tests · Check derive counts and assumptions against live FalkorDB; localhost:6379 was unavailable here
- 2026-10-16 · Codex · Counted latest PR review and issue comment activity, refreshed lastSeen from all supported activity, and expanded assumption checks g–i · Re-run pytest and live checks after starting FalkorDB
- 2026-10-16 · Codex · Fixed REVIEWED.at loading and added marked end-to-end Cypher integration coverage for loader and derive behavior · Integration test skips without FalkorDB; run against a live server to verify query execution
- 2026-10-16 · Codex · Matched FalkorDB duplicate-index wording, isolated assumption check h, and bound Docker ports to localhost · Verify integration test against live FalkorDB 4.22.0
- 2026-10-16 · Codex · Added WP4 issue/document/title IMPLEMENTS linking, confidence-aware participation, and keyword tests; live run found 26 issue-ref, 27 rfc-doc, and 258 title matches · Review keyword precision/examples and confirm live graph counts
- 2026-10-16 · Codex · Added Component loading, component expertise, component bus-factor/departure queries, and orphaned-file reporting with tests · Rebuild the graph with `load all`, `link_decisions`, and `derive`; review component summary and `try_queries.py` output
- 2026-10-16 · Codex · Refined Component path fallbacks, isolated test resources, bucketed file-only paths, and added minimum-area totals to bus-factor queries · Rebuild graph and review fallback counts and filtered bus-factor tables
- 2026-10-16 · Codex · Added requested Spark/Kernel package roots, versioned Scala roots, exact component-edge replacement, and stale-node cleanup; fallback report now groups deterministic placement rules · Check the 74 reverse-DNS fallback paths and live departure tables
