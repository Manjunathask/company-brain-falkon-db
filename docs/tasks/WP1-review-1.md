<review>
Reviewer (Claude Code) feedback on WP1. Overall good: counts match, code is readable, tests pass.
Fix the items below, keep everything else as is.
</review>

<fixes>
1. Login case (correctness, high). GitHub logins are case-insensitive but appear in different cases:
   CODEOWNERS has `@TimothyW553`, noreply emails are lower-cased, and the API returns canonical case.
   Today these would become two Person nodes and break departure impact. Make the Person key
   the lower-cased login everywhere: add identity.normalize_login(handle) (strip `@`, lower-case) and use
   it in resolve_person_key (api_map values and noreply logins) and for CODEOWNERS owners. Keep the original
   spelling as `p.handle` when we have it (CODEOWNERS now, API later). Add tests for the mixed-case case.
2. Person properties overwritten per commit (correctness, medium). In 01_load_commits.cypher,
   `SET p.authorEmail = ..., p.name = ...` keeps whichever commit ran last. A person with several emails
   should keep all of them: store `p.emails` as a de-duplicated list (append only if not present) and set
   `p.name` only when it is null (coalesce). Drop `p.authorEmail`.
3. Index step is not re-runnable (AGENTS.md: re-running any step must be safe). FalkorDB raises an error
   when an index already exists. Make the index step tolerate exactly that error per statement (print
   "exists") and re-raise anything else. Put this in one place: db.create_indexes(graph). Remove the
   duplicated line-splitting logic from db.run_query and load.py.
4. AGENTS.md says run_query(name, params) loads queries/<name>.cypher, so callers pass the name without
   the extension (e.g. run_query("05_bus_factor", {...})). Make load_query accept the bare name (still
   reject path separators and `..`). Update callers and the test.
5. Query file numbering must line up with PLAN.md, where query 3 is the KNOWS derive. Rename
   03_load_codeowners.cypher -> 02c_load_codeowners.cypher. Convention for the rest of the project:
   the number is the PLAN.md query number; extra loaders take a letter suffix (01b, 01c, 02c ...).
6. 01b_link_part_of.cypher: write it as
   `MATCH (c:Commit) WHERE c.pr IS NOT NULL MATCH (pr:PR {number: c.pr}) MERGE (c)-[:PART_OF]->(pr)`
   so the PR lookup uses the PR.number index instead of a cartesian product. Explain the shape in the header.
7. 02_load_decisions.cypher: the RFC File node should also get IN_MODULE to its Module (first path segment,
   i.e. protocol_rfcs) like every other File. Pass the module in the row from rfcs.py.
8. The API identity map file: WP2 will write data/raw/identities.json as {email: login-or-null}. Move the
   map loading into identity.load_api_map() reading that file (null values mean "no GitHub user"), and use
   it from load.py. Remove the email_to_login.json name.
9. docker-compose.yml: pin `falkordb/falkordb:v4.22.0` (released 2026-09-30; v4.10.0 is from June 2025 and
   predates the algorithms the plan uses). The data path /var/lib/falkordb/data is confirmed by
   docs.falkordb.com/operations/persistence; update the comment to say persistence across restart is still
   to be checked. Add `restart: unless-stopped`.
10. README setup: give the exact clone command
    `git clone -c core.longpaths=true https://github.com/delta-io/delta.git data/delta`
    (Windows long paths broke a plain clone) and use `uv run python -m ...` in commands.
11. Delete docs/tasks/wp1.md (duplicate of the brief). Do not edit other files in docs/tasks/.
</fixes>

<verification_loop>
Run `.venv/Scripts/python -m pytest -q` and the three ingest commands again; all must pass with the same
counts (2234 commits, 19 RFCs, 9 rules). Also print the distinct Person keys that the commit loader would
create (count only) and how many of them start with `email:`.
</verification_loop>

<compact_output_contract>
Reply with: each fix number and what you changed (one line each); pytest summary; ingest counts; the
Person-key counts; anything you disagree with and why.
</compact_output_contract>
