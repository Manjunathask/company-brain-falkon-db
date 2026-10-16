<review>
Reviewer (Claude Code) feedback on WP2. Good structure: cache-first, cursors, alias batches, tests.
Fix the items below and keep everything else.
</review>

<fixes>
1. Errors are cached (correctness, high). _request writes the payload to the cache before checking
   `errors`, so one transient or partial error is replayed from cache forever. Change to:
   - retry (not cache) on GraphQL errors whose type is RATE_LIMITED or whose message mentions
     "secondary rate limit", "timeout" or "Something went wrong", with the same backoff;
   - in alias batches (identities, referenced PRs), errors of type NOT_FOUND are expected (for example a
     `(#N)` number that is an issue, not a PR): keep the partial `data`, cache it, and log the missing
     numbers; any other error type raises and is NOT cached.
   Add a test for each path (retry-then-success, NOT_FOUND partial batch cached, other error not cached).
2. One source of truth for bots. Move is_bot to identity.py (next to normalize_login), and also treat the
   login `ghost` (GitHub's placeholder for deleted accounts) as a bot. Remove the hard-coded bot list from
   01c/01d Cypher. Commit authors must get the flag too: load.py computes `authorBot` per commit row with
   is_bot(author key) and 01_load_commits sets `p.bot = coalesce(p.bot, false) OR c.authorBot`.
3. No dynamic map access in Cypher. `row.reviewerHandles[reviewer]` may not be supported by FalkorDB and is
   hard to explain. Emit reviewers and commenters as lists of maps {login, handle, bot} from Python and use
   `UNWIND row.reviewers AS r MERGE (p:Person {login: r.login}) SET p.handle = coalesce(p.handle, r.handle),
   p.bot = coalesce(p.bot, false) OR r.bot`.
4. Drop the FOREACH/CASE for a null author: map a null PR/issue author to `ghost` in Python (it is what
   GitHub itself shows for deleted users; bot=true per fix 2), so the Cypher is plain MERGE. Update the header
   comments to explain this.
5. Replace `__import__("busfactor.db", ...)` and `__import__("sys")` with normal imports.
6. The PR page size: use 25 per page for the main pagination (PR bodies plus 30 reviews per PR can make
   50-node pages time out). Keep 40 for the alias batches.
7. In identity.py, resolve_person_key scans the whole api_map for every call; load_api_map already
   lower-cases keys, so use a dict lookup on the lower-cased address.
</fixes>

<verification_loop>
`.venv/Scripts/python -m pytest -q` must pass, and `python -m busfactor.ingest.github_api all` without a
token must still exit with the clear message.
</verification_loop>

<compact_output_contract>
One line per fix with what changed; pytest summary; anything you disagree with and why.
</compact_output_contract>
