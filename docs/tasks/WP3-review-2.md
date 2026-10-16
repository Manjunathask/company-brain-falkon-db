<review>
Reviewer (Claude Code) feedback on WP3 round 2. Fixes 1-4 look right except one bug, which also shows
we need tests that execute the Cypher.
</review>

<fixes>
1. Bug: queries/01c_load_prs.cypher sets `review.at` from `row.at` (the PR row, which has no `at`) instead
   of `r.at` (the reviewer map). REVIEWED.at would always stay null and reviewers would never count as
   active. Use `r.at`, same shape as COMMENTED in 01d.
2. Add tests/test_graph_integration.py, marked `@pytest.mark.integration`, skipped automatically when
   FalkorDB at FALKORDB_HOST:FALKORDB_PORT is unreachable. It loads small hand-written rows through the real
   query files into a throwaway graph `bf_test` (delete it before and after) and asserts:
   - 00 indexes run twice without error (db.create_indexes);
   - commits load: Person/Commit/File/Module counts, TOUCHED added/deleted, p.emails de-duplicated across two
     commits with two emails for one login, bot author gets p.bot = true;
   - PRs load: OPENED, REVIEWED with REVIEWED.at = the latest review time, ghost author, reviewer bot flag;
   - part_of links only commits whose pr matches a loaded PR;
   - issues load: COMMENTED.at; references link only to existing Issue nodes;
   - decisions + codeowners load: TRACKED_IN, DOCUMENTED_IN, IN_MODULE for the RFC file, SUPERSEDED_BY,
     DECLARED_OWNER with mixed-case CODEOWNERS handle landing on the lower-cased Person;
   - derive: KNOWS commits counted DISTINCT (one commit touching two files in one module counts once);
     a reviewer-only person with a recent REVIEWED.at is :Active and has lastSeen set, lastCommit null;
     a bot never gets KNOWS/WORKS_WITH/Active; WORKS_WITH respects minShared and the hub-file cut;
     re-running derive gives identical counts (idempotence).
   Register the marker in pyproject.toml. Plain `pytest -q` runs it when the DB is up and skips it otherwise.
</fixes>

<verification_loop>
`.venv/Scripts/python -m pytest -q` must pass (integration tests skipped here, since the sandbox cannot
reach the DB). Report how many tests are skipped.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary including skipped count; anything you disagree with.
</compact_output_contract>
