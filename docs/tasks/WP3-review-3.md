<review>
Reviewer (Claude Code) ran the suite and scripts/check_assumptions.py against a live FalkorDB 4.22.0
(Docker). Results: a-f and i PASS (GRAPH.COPY exists; betweenness and WCC work). Two problems:
</review>

<fixes>
1. Live duplicate-index error text is exactly: `Attribute 'login' is already indexed`.
   db.is_duplicate_index_error must match that (match on "is already indexed"; drop the guessed
   "Index already exists"). Update the unit test to use the real message. The integration test currently
   fails on this.
2. check_assumptions.py check (h) is contaminated: check (e) leaves WORKS_WITH edges in `bf_check`, so the
   WORKS_WITH case reports cleared=3. The query shape itself is fine (rebuilt counts are 1 and 1). Run each
   check on a clean graph (delete and recreate `bf_check` per check, or clear all nodes first) so checks are
   independent.
3. Security: docker-compose.yml publishes 6379 and 3000 on all interfaces with no password. Bind both to
   localhost: "127.0.0.1:6379:6379" and "127.0.0.1:3000:3000". Add a one-line comment why.
</fixes>

<verification_loop>
`.venv/Scripts/python -m pytest -q` (the integration test will skip in your sandbox; the reviewer runs it live).
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary.
</compact_output_contract>
