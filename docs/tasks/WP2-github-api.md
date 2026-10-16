<task>
You are implementing work package WP2 of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md,
docs/PLAN.md and docs/PROGRESS.md first and follow them. WP1 (git loaders, db.py, load.py, queries/)
is done and committed; reuse its helpers (db.batched, db.run_query(name-without-extension),
identity.normalize_login / resolve_person_key / load_api_map, load.py CLI style).
Conventions set in WP1 review: Person.login is always the lower-cased GitHub login (normalize_login);
the original spelling goes in p.handle. Query file numbers follow PLAN.md; extra loaders take a letter
suffix. Every author, reviewer and commenter login from the API must go through normalize_login.

Scope of WP2: fetch PRs, reviews, RFC issues and the author-email -> login map from the GitHub GraphQL
API for delta-io/delta, cache every raw response, and load them into the graph. You have no network
access and no token: write the code and test it against fixture JSON. The reviewer will run the real
fetch afterwards.

Build:
1. src/busfactor/ingest/github_api.py, using httpx against https://api.github.com/graphql with
   `Authorization: bearer $GITHUB_TOKEN` (read from .env; never print it).
   - Cache: every raw response goes to data/raw/github/<kind>/<key>.json BEFORE parsing. If the cache file
     exists, read it and do not call the API. A `--refresh` flag bypasses the cache.
   - Every query also selects `rateLimit { cost remaining resetAt }`. If remaining < 50, sleep until
     resetAt. Retry 502/503 and secondary rate limits with exponential backoff (max 5 tries).
     Fail loudly on GraphQL `errors`.
   - prs: repository(owner:"delta-io", name:"delta").pullRequests(first: 50, orderBy:{field: CREATED_AT,
     direction: DESC}) paginated with cursors, stopping once createdAt < GIT_SINCE. Per PR: number, title,
     state, createdAt, mergedAt, body, author{login}, reviews(first: 30){nodes{author{login} state submittedAt}}.
     Then a second pass: PR numbers referenced by commits (data/raw/git_log.json `pr`) that were not
     fetched (created before the window) are fetched by number in batches of 40 using GraphQL aliases.
   - identities: for each distinct author email in git_log.json pick one commit sha and query
     repository.object(oid:) ... on Commit { author { email user { login } } } in alias batches of 50.
     Write data/raw/identities.json as {email: login-or-null} (keep the API's spelling of the login here;
     identity.load_api_map already reads this file and normalize_login lower-cases it).
   - rfc_issues: the 19 RFC issue numbers from rfcs.py. Per issue: number, title, state, createdAt,
     author{login}, comments(first: 100){nodes{author{login} createdAt}} (paginate if hasNextPage).
   - CLI: `python -m busfactor.ingest.github_api {identities,prs,rfc_issues,all}` printing counts and
     the rate limit left. Order for `all`: identities, prs, rfc_issues.
   - Bots: keep them, but mark logins ending in `[bot]` or known bots (dependabot, github-actions)
     so the loader can set `p.bot = true`.
2. Parsing to plain rows (pure functions, unit-tested): prs -> {number, title, state, createdAt, mergedAt
   (epoch ms or null), body, author, reviewers:[distinct logins excluding the author]}; issues ->
   {number, title, state, createdAt, author, commenters:[distinct logins]}.
   references(pr_body) -> set of issue numbers cited as `#N`, `delta-io/delta#N` or
   `https://github.com/delta-io/delta/issues/N` (also /pull/N), on word boundaries.
3. queries (header comment on each: what it answers, parameters, why this shape):
   01c_load_prs.cypher (PR node; Person-[:OPENED]->PR; Person-[:REVIEWED]->PR), 01d_load_issues.cypher
   (Issue node SET title/state/createdAt; Person-[:OPENED]->Issue; Person-[:COMMENTED]->Issue),
   01e_link_references.cypher (PR-[:REFERENCES]->Issue only where the Issue node already exists, i.e.
   the RFC issues; MATCH, not MERGE, on the Issue). Keys: PR.number, Issue.number, Person.login.
   Note: GitHub PRs and issues share one number space; keep PR and Issue as separate labels.
4. load.py: add subcommands prs, issues, references, and make `all` run in this order: indexes, commits,
   decisions, codeowners, prs, part_of, issues, references. Person keys for commit authors must go
   through identity.resolve_person_key so git authors and API logins land on the same Person node.
5. tests/: fixtures under tests/fixtures/github/ (small hand-written GraphQL responses) covering
   pagination stop at GIT_SINCE, the alias batch for identities (one email with user null), reviewer
   de-duplication, references() including a false positive to avoid (e.g. "#1a" or "issue 4381" without #),
   and the cache-hit path (no HTTP call when the cache file exists; monkeypatch httpx).
6. Append one line to docs/PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta.
Do not run git commit. Plain readable code. Never log or write the token anywhere.
</action_safety>

<verification_loop>
Run and make pass: `.venv/Scripts/python -m pytest -q`. Also run
`.venv/Scripts/python -m busfactor.ingest.github_api all` once without a token and confirm it exits
with a clear "GITHUB_TOKEN not set" message rather than a traceback.
</verification_loop>

<compact_output_contract>
Reply with: files created/changed; pytest summary line; estimated number of API calls and rate-limit
cost for a full run; decisions the reviewer should check (with reasons); anything uncertain; "needs".
</compact_output_contract>
