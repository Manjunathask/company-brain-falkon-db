<task>
You are implementing work package WP1 of "Bus Factor", a hackathon project (Graph Hacks, FalkorDB).
Read these first and follow them exactly: AGENTS.md (hard rules, layout, how to work), docs/PLAN.md
(graph model and the 13 Cypher queries), docs/PROGRESS.md.

Scope of WP1: everything that comes from the local git clone, plus the DB plumbing. No GitHub API, no
running database yet (FalkorDB is not up on this machine; Docker is being installed by the user).

Already in place (do not redo): git repo, pyproject.toml with deps falkordb, httpx, python-dotenv,
pytest (dev), a uv-managed .venv at .venv/ (run things with `.venv/Scripts/python -m ...`),
src/busfactor/__init__.py, and a full clone of delta-io/delta at data/delta (gitignored).
You have no network access. If you need a new dependency, do not add it; list it under "needs" in your report.

Build:
1. docker-compose.yml: FalkorDB image `falkordb/falkordb` (pin a specific tag you can justify; say which),
   ports 6379 and 3000, a named volume. The data path inside the image is uncertain (/data vs
   /var/lib/falkordb/data); mount the one you believe is right and add a comment that it must be
   verified once Docker is up. Allow FALKORDB_ARGS to be passed through.
2. .env.example: GITHUB_TOKEN, FALKORDB_HOST, FALKORDB_PORT, FALKORDB_PASSWORD (empty default),
   FALKORDB_GRAPH=delta, DELTA_REPO=data/delta, GIT_SINCE=2024-10-15. Load .env with python-dotenv.
3. src/busfactor/db.py: get_graph() using the official `falkordb` package (confirm the API by reading
   the installed package source under .venv/Lib/site-packages/falkordb, not from memory);
   load_query(name) reading queries/<name>.cypher; run_query(name, params) ; batched(items, size=500).
   Keep it small and readable.
4. src/busfactor/ingest/git_log.py: run `git -C <DELTA_REPO> -c core.quotepath=off log --since=<GIT_SINCE>
   --no-merges --no-renames --numstat` with a custom --format using unit/record separators. Use the
   committer timestamp (%ct) as `ts` in epoch milliseconds. Produce one dict per commit:
   {sha, ts, subject, area, pr, authorEmail (lower-cased), authorName, files: [{path, module, added, deleted}]}.
   - area: first leading `[Tag]` in the subject, lower-cased and stripped, else null.
   - pr: int from a trailing `(#N)` in the subject, else null.
   - module: first path segment; root-level files -> "root".
   - binary files show `-` in numstat: store added/deleted as 0 for those.
   Write the parsed list to data/raw/git_log.json. `python -m busfactor.ingest.git_log` prints:
   commit count, distinct author emails, distinct files, modules with commit counts, how many commits
   have a PR number, and the top 10 area tags.
5. src/busfactor/ingest/identity.py: resolve_person_key(email, api_map) -> str. Order: api_map
   (email -> GitHub login, filled later by the API loader from data/raw) wins; else a GitHub noreply
   address (`12345+login@users.noreply.github.com` or `login@users.noreply.github.com`) gives the login;
   else `email:<address>`. Never guess a login from a name.
6. src/busfactor/ingest/rfcs.py: parse the three markdown tables (Proposed, Accepted, Rejected) in
   data/delta/protocol_rfcs/README.md. The tables have different columns (Proposed has 4, the others 5).
   Output per RFC: {slug, title, status ('proposed'|'accepted'|'rejected'), proposedOn, decidedOn
   (epoch ms or null), issue (int), path (repo-relative path of the RFC file)}. Take slug and path from
   the link URL, not the link text: one link text is a typo (`column-mapping-usage.tracking.md`).
   Expect exactly 19 RFCs: 11 proposed, 7 accepted, 1 rejected. Fail loudly if the count differs.
   `python -m busfactor.ingest.rfcs` prints them as a table.
7. src/busfactor/ingest/codeowners.py: parse data/delta/.github/CODEOWNERS into
   {pattern, module, owners:[handles without @]} rows. module = first path segment of the pattern;
   `/*` and root-level files like `/build.sbt` -> "root". Expect 9 rules. Print them.
8. queries/ (one file per query, each with a header comment: what it answers, its parameters, why it is
   shaped that way): 00_indexes.cypher (one CREATE INDEX per line; db.py may split on lines),
   01_load_commits.cypher (Person/Commit/AUTHORED/File/Module/IN_MODULE/TOUCHED; store c.pr as a
   property on Commit; do NOT link PART_OF here), 01b_link_part_of.cypher (second pass: link Commit
   to PR by Commit.pr once PRs are loaded; order-independent, replaces the FOREACH/CASE trick in PLAN.md),
   02_load_decisions.cypher, 02b_superseded_by.cypher, 03_load_codeowners.cypher (DECLARED_OWNER
   {pattern} Person -> Module). Person.login is the stable key; store authorEmail on Person too.
   Use MERGE on stable keys and UNWIND $rows so re-runs are safe.
9. src/busfactor/load.py: CLI `python -m busfactor.load {indexes,commits,decisions,codeowners,part_of,all}`
   that reads the parsed data and runs the queries in batches of 500, printing node/relationship counts
   after each step. It cannot be run yet; make it fail with a clear message if FalkorDB is unreachable.
10. tests/: pytest unit tests for git_log parsing (feed a small captured git output string, including a
   binary file, a root-level file, a subject with `[SPARK]`, one without a PR number), identity,
   rfcs (run against the real README in data/delta, skip if missing), codeowners, and load_query.
11. README.md: short skeleton (what it is, setup steps so far, graph model pointer to docs/PLAN.md)
    and a "Built with AI assistance" section stating that Claude Code (reviewer/orchestrator) and
    OpenAI Codex (implementation) were used, with briefs in docs/tasks/.
12. Append one line to docs/PROGRESS.md: `2026-10-16 · Codex · <what changed> · <what to check>`.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, or anything under data/delta.
Do not run git commit; the reviewer commits after review. Plain, readable code; no frameworks that hide
the Cypher. No vector store, no pandas path that answers questions.
</action_safety>

<verification_loop>
Before finishing, run and make pass:
- `.venv/Scripts/python -m pytest -q`
- `.venv/Scripts/python -m busfactor.ingest.git_log` (expect about 2,234 commits, about 2,231 with a PR)
- `.venv/Scripts/python -m busfactor.ingest.rfcs` (exactly 19)
- `.venv/Scripts/python -m busfactor.ingest.codeowners` (9 rules)
Fix anything that fails. Do not claim a check passed unless you ran it.
</verification_loop>

<compact_output_contract>
Reply with: files created/changed; the exact output of the three ingest commands (trimmed to counts);
pytest summary line; decisions you made that the reviewer should check (with reasons); anything left
undone or uncertain; "needs" (dependencies or user actions).
</compact_output_contract>
