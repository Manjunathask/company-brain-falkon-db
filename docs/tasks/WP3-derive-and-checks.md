<task>
You are implementing work package WP3 of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md,
docs/PLAN.md (section "Derive" and "Test these first on Thursday") and docs/PROGRESS.md first.
WP1 (git loaders, db.py, load.py, queries/) and WP2 (GitHub API loader) are done; follow their
conventions (query naming, header comments, db.run_query, batched, CLI style).
Conventions: db.run_query takes the query name without `.cypher`; Person.login is the lower-cased login;
query file numbers follow PLAN.md with letter suffixes for extra steps.

Scope of WP3: the derive step and an assumptions checker. The sandbox you run in may not reach the
database; write the code so the reviewer can run it, and unit-test what can be tested without a DB.

Build:
1. Query files (header comment on each: what it answers, parameters, why this shape), taken from PLAN.md
   "Derive" and adjusted only where needed:
   03_derive_knows.cypher            Person-[:KNOWS {commits, lastTouched}]->Module, count(DISTINCT c)
   03b_derive_last_seen.cypher       SET p.lastSeen; SET p:Active where lastSeen > $since.
                                     First REMOVE :Active from everyone so re-runs are correct.
   04_derive_works_with.cypher       WORKS_WITH {sharedFiles} for pairs with id(a) < id(b), commits after
                                     $since, sharedFiles >= $minShared. Skip "hub" files touched by more than
                                     $maxFileCommits commits in the window (build.sbt-style files make every
                                     pair look connected). Delete existing WORKS_WITH first so re-runs are exact.
   04b_derive_participated_pr.cypher   via OPENED|REVIEWED PR -[:IMPLEMENTS]-> Decision
   04c_derive_participated_issue.cypher via OPENED|COMMENTED Issue <-[:TRACKED_IN]- Decision
   Store PARTICIPATED_IN {via: 'pr'|'issue'} and keep both paths idempotent (MERGE on (p, d) then SET).
   Bots (p.bot = true) must not get KNOWS, WORKS_WITH, Active or PARTICIPATED_IN.
2. src/busfactor/derive.py: `python -m busfactor.derive` runs them in order with defaults
   since = now - 365 days (epoch ms), minShared = 3, maxFileCommits = 150 (all overridable by flags),
   times each query, and prints after each: relationships created/total, and a sanity table:
   top 10 modules by number of KNOWS edges; number of Active people; WORKS_WITH edge count and
   the top 5 pairs by sharedFiles; PARTICIPATED_IN count per decision.
3. scripts/check_assumptions.py (run by the reviewer against a live FalkorDB): for each item in PLAN.md
   "Test these first", run a tiny self-contained check in a throwaway graph named `bf_check` (delete it at
   the end) and print PASS/FAIL with evidence:
   a) SET p:Active / REMOVE p:Active work and MATCH (:Active) reflects them;
   b) reduce() with a map accumulator works, and ORDER BY before collect() keeps the order;
   c) FOREACH + CASE trick for an optional MERGE works (kept for the record even though we link PART_OF
      in a second pass);
   d) whether GRAPH.COPY exists (call it via the redis client; report the error text if not);
   e) algo.betweenness and algo.WCC with nodeLabels/relationshipTypes run and return rows;
   f) the FalkorDB server version (GRAPH.INFO or INFO / MODULE LIST).
4. tests/: unit tests that every derive query file loads, has a header, and declares the parameters
   derive.py passes (parse `$name` tokens from the file and compare).
5. Append one line to docs/PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta.
Do not run git commit. Plain readable code.
</action_safety>

<verification_loop>
Run and make pass `.venv/Scripts/python -m pytest -q`. If a FalkorDB at localhost:6379 is reachable from
your sandbox, also run `python -m busfactor.derive` and `python scripts/check_assumptions.py` and include
their output; if not, say so plainly.
</verification_loop>

<compact_output_contract>
Reply with: files created/changed; pytest summary; derive/check output if you could run it; decisions the
reviewer should check (with reasons); anything uncertain.
</compact_output_contract>
