<task>
You are implementing work package WP6b of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md, docs/PLAN.md,
docs/PROGRESS.md and docs/QUERIES.md. WP1-WP6 are done; follow their conventions (query files with headers,
no Cypher in src/, read-only tools via ro_query, PLAN numbering with letter suffixes, integration tests on
bf_test). FalkorDB is reachable; pipeline: load all -> link_decisions -> derive.

Why (reviewer findings on the live graph, scouting the demo):
- allisonport-db shows 1,303 "orphaned files". 1,150 of them come from one commit, "[Infra] Remove remaining
  connectors from master (#5620)", which deleted those files. A deleted file is not knowledge at risk.
- Mass-change commits inflate expertise: 8 commits touch more than 100 files (connector removal 1,150, Java 11
  upgrade 308, docs-site redesign/revert ~190 each, Spark 3.5 drop 157, generatedsuites regroup 106, the
  io.delta.kernel.spark -> io.delta.spark.internal.v2 rename 105). They are 0.4% of commits but 17% of file
  touches. With --no-renames a move shows up as delete + add and credits the mover with every file.
- orphaned_decisions returns no rows for any of the top 15 authors: RFC issue commenters keep every decision
  "covered", so the metric never fires. The demo needs a sharper decision question.

Build:
1. File existence. In ingest (git_log.py or a small new ingest/head_files.py), read `git -C <DELTA_REPO> ls-files`
   at HEAD and give each file row `exists` (true/false). Load it onto File.exists (default true for RFC doc files
   that exist). Deleted files keep their history (commits still TOUCHED them) but are excluded from: 06b orphaned
   files, 08 successor shared files, and their evidence queries. Say in each header why.
2. Bulk commits. Mark Commit.bulk = true when the commit touches more than $maxCommitFiles files (default 100,
   one place in the code, printed by derive). Exclude bulk commits from KNOWS (module and component), WORKS_WITH,
   06b and 08. Keep them in the graph (AUTHORED/TOUCHED stay) so the decision trace and drift still see them.
   Print in derive which commits were marked bulk (sha, files, subject).
3. Decision ownership. New tool query 07b_decision_share.cypher: for $login, the decisions where they opened at
   least $minShare (default 0.3) of the PRs that IMPLEMENTS the decision at confidence >= $minConfidence; return
   decision, status, theirPRs, totalPRs, share, and the other PR openers who are still Active with their PR
   counts (the people to ask). Add the tool `decision_share` to tools.py with a specific evidence query
   (07b_decision_share_graph: Person -OPENED-> PR -IMPLEMENTS-> Decision for that person and the others).
   Keep 07 as is.
4. Re-run the full pipeline live and re-run the reviewer's scouting table for the top 15 authors by commits:
   login, orphaned files, ORPHANED components, AT RISK components, decision_share rows (share >= 0.3).
5. Tests: deleted file not orphaned; bulk commit excluded from KNOWS but still in the trace; decision_share on a
   fixture (one person with 2 of 3 implementing PRs -> share 0.67, others listed). Update QUERIES.md and PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta (read-only git
commands are fine). Do not run git commit. Tools stay read-only.
</action_safety>

<verification_loop>
pytest including integration tests must pass. Include the scouting table, the list of bulk commits, and the count of
File nodes with exists = false.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; bulk commit list; deleted-file count; scouting table; decisions for the reviewer.
</compact_output_contract>
