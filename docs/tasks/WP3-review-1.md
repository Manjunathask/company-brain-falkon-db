<review>
Reviewer (Claude Code) feedback on WP3. The derive queries are close to PLAN.md and readable. Fix these.
</review>

<fixes>
1. Activity must not mean "committed" only (correctness, high). Query 7 ("who to ask") and the departure
   simulator use p.lastSeen / :Active. A maintainer who mostly reviews (tdas owns most CODEOWNERS paths)
   would look inactive. Make lastSeen the latest of any activity:
   - WP2 parse_pr: for each reviewer keep the latest review submittedAt (epoch ms) as `at`; parse_issue:
     for each commenter keep the latest comment createdAt as `at`. 01c sets `REVIEWED.at`, 01d sets
     `COMMENTED.at` (keep the max if the edge exists). Update fixtures/tests.
   - 03b: compute p.lastCommit = max authored commit ts, and p.lastSeen = max of lastCommit, opened PR
     createdAt, REVIEWED.at, COMMENTED.at (ignore nulls). :Active = lastSeen > $since and not a bot.
     Explain in the header why activity includes reviews.
2. 04b clears only bot PARTICIPATED_IN edges, so stale edges for people stay after the evidence goes away.
   Delete all PARTICIPATED_IN at the start of 04b (04b always runs before 04c), like KNOWS and WORKS_WITH.
3. check_assumptions.py must also check the shapes our own code relies on:
   g) run CREATE INDEX twice on the same label/property and print the exact error text of the second
      call; report PASS only if db.create_indexes would tolerate it (import and reuse its matching rule,
      do not duplicate the string);
   h) the `OPTIONAL MATCH ()-[old:X]->() DELETE old WITH count(old) AS cleared MATCH ...` shape used by
      03 and 04: run it once with existing edges and once with none, and check the rebuilt edge count;
   i) reduce() over a list containing nulls filtered by a list comprehension (the 03b lastSeen shape).
4. Nothing else changes. Keep query numbering.
</fixes>

<verification_loop>
`.venv/Scripts/python -m pytest -q` must pass.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; anything you disagree with and why.
</compact_output_contract>
