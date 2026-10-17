<review>
A pre-submission review (Codex on GPT-6-Astra, then checked by Claude Code against the code and the live `delta`
graph on 2026-10-17) found that several headline numbers do not measure what their labels say. A judge who opens the
Cypher will see it, so this package comes before any new feature.

Verified findings:
1. Time window mismatch. `03_derive_knows` / `03c_derive_knows_component` store `KNOWS.commits` over ALL loaded history
   (2 years) and `KNOWS.lastTouched` = latest commit. `05_bus_factor`, `05b_bus_factor_component`,
   `06_departure_impact`, `12_declared_vs_actual` and `15b_refresh_component_risk` filter on `k.lastTouched > $since`
   but then use the full `k.commits`. Someone with 100 old commits and 1 recent one counts as 101 "recent" commits.
   The UI says "risk uses the last 12 months and at least 2 commits".
   Live: current 05b = 87 reportable areas, 42 with bus factor 1. Counting only commits with `c.ts > $since`
   (same minCommits 2 / minTotal 5) = 69 reportable, 25 with bus factor 1.
2. The leaving person has no threshold. `06_departure_impact` applies `$minCommits` to the people who remain but not to
   the person leaving. murali-db's five "ORPHANED" areas: spark-unified/sql (3 commits), build/(files),
   kernel/kernel-api/exceptions, spark-unified/spark-4.0-4.1, spark/metering (1 commit each).
3. Reviews are ignored. Active reviewers of PRs with recent commits touching those areas: spark-unified/sql 7,
   spark/metering 7, kernel/kernel-api/exceptions 6, build/(files) 4, spark-unified/spark-4.0-4.1 1. "No expert left"
   overstates what authorship alone shows.
4. Decision links are mostly guesses. IMPLEMENTS: 230 `title-keyword` (confidence low) vs 26 `issue-ref` + 27
   `rfc-doc` (high). scottsand-db's "Catalog-Managed Tables, 43 of 88 PRs" is 1 of 3 on explicit links only. The UI
   shows the combined number with no split.
5. `06_departure_impact_graph` draws KNOWS edges for every active person on those components, not only the people the
   table counted (no window, no threshold), so the evidence graph can disagree with the table.

Under the strict rules (2+ in-window commits on both sides), harperjiang is the only recent active author of
`flink/kernel`, `flink/(files)` and `flink/inttest`; seewishnew, jasonschen3 and chengjix also hold several
single-author areas. murali-db mostly drops out. The demo hero will be re-picked from your report.
</review>

<task>
Make every risk number count exactly what its label says, add reviews as a second, separately shown signal, and split
decision links by confidence. Read AGENTS.md, docs/PLAN.md (graph model) and docs/QUERIES.md first.

1. Windowed counts. In 05, 05b, 06, 12 and 15b count distinct qualifying commits with `c.ts > $since` directly from
   `(p:Person)-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT|IN_MODULE]->(area)`, with the same
   exclusions as 03/03c (non-bot, `c.bulk` false, `f.exists` true). Do not rely on `k.commits` for anything labelled
   recent. The same applies to `08_successor`'s `theirCommits` column (shown as "Commits here"): count in-window
   commits. Keep KNOWS and its all-history `commits` as they are (other tools and the snapshot use them); say in each
   header comment why the windowed count is computed from commits. Aggregate with `count(DISTINCT c)` per person and
   area BEFORE ranking (AGENTS.md: unreferenced relationships only check existence).
2. Same threshold for the leaving person. In 06, report only areas where the leaving person has at least `$minCommits`
   in-window commits. Areas below the threshold are not exposure; do not return them.
3. Precise risk codes. Rename the codes everywhere (queries, tools, api, agent prompt and followups, web, tests):
   `ORPHANED` -> `NO OTHER AUTHOR`, `AT RISK` -> `ONE OTHER AUTHOR`, `COVERED` stays. Grep for every use, including
   `15b` and anything that compares refresh risk before/after.
4. Reviewer signal. In 06 add `reviewers` (up to 5 logins, most area PRs reviewed first) and `reviewerCount`: distinct
   Active, non-bot people other than the leaving person with a `REVIEWED` edge (`review.at > $since`) to a PR that has
   an in-window, non-bulk commit (`PART_OF`) touching a current file in that component. Aggregate the remaining
   authors first, then the reviewers in a separate WITH stage, so one cannot multiply the other. Reviewers do NOT change
   the risk code; they are shown beside it. Add `reviewers` and `reviewerCount` to the departure summary:
   `noOtherAuthor`, `noOtherAuthorOrReviewer` (risk NO OTHER AUTHOR and reviewerCount 0), `oneOtherAuthor`.
5. Graph companions match their tables. 05b and 05 return `countedExperts`: the logins counted to reach half the
   total. `05*_graph` draws KNOWS paths for exactly those logins instead of re-ranking `k.commits`. `06_graph` draws
   KNOWS for the leaving person and the `remaining` logins from the rows only, plus REVIEWED->PR paths for the listed
   reviewers (cap 3 PRs per reviewer per area).
6. Decision confidence split. 07b returns, per decision, `theirExplicitPRs`, `explicitPRs` (high confidence) and
   `theirTitleMatchPRs`, `titleMatchPRs` (low) next to the existing combined `theirPRs`/`totalPRs`/`share`; keep
   `$minShare`/`$minConfidence` filtering as is. Sort explicit share first.
7. Honest copy (web/app.js, web/index.html, agent/prompt.py, api/app.py strings). Use names or "they", never inferred
   pronouns. Suggested wording; keep it short:
   - "What is a bus factor?": the number of people who wrote at least half of an area's commits in the last 12 months,
     counting people with 2+ commits there and areas with 5+ such commits. A bus factor of 1 means one person wrote at
     least half. It measures who wrote the code, not who understands it: reviewers and people off GitHub can know it too.
   - `/api/summary` `dataWindow`: "2 years loaded; risk counts commits from the last 12 months; a person needs 2+ such
     commits in an area".
   - Leave sentence: "If <name> left: <n> code areas where they made 2+ commits in the last 12 months would have no other
     recent author (<m> of them were reviewed by other active people), <k> would have one other recent author, ..."
     then files and cut-off people as now.
   - Sections: "No other recent author · n", "One other recent author · n", "Decisions they worked on · n".
   - Area card: their recent commits here; other recent authors; "Reviewed by: tdas, … (n active reviewers)" or, when
     there are none, "Nobody else authored or reviewed this code in the last 12 months" (sort these first).
   - Decision card: "Explicitly linked PRs: they opened a of b · Title match only: c of d", with a one-line note that
     title matches are keyword guesses.
   - Agent system prompt: describe the risk codes in these terms, tell it to mention reviewers when a code is
     NO OTHER AUTHOR, and to say "no other recent author" rather than "nobody knows this".
8. docs/QUERIES.md: update the entries for every query you changed (what it answers, parameters, why this shape).
</task>

<action_safety>
Edit only queries/**, src/busfactor/** (tools.py, api/app.py, agent/prompt.py, agent/followups.py and anything that
uses the risk codes), web/**, tests/** and docs/QUERIES.md. Do not touch README.md, docs/DEMO.md, docs/BLOG.md,
docs/PROGRESS.md, AGENTS.md, CLAUDE.md, docs/PLAN.md or docs/tasks/. Read-only against the live `delta` graph (use
`ro_query`; no derive or load runs on `delta`; the integration tests' throwaway graphs are fine). No live LLM calls.
Do not run git commit. Never mention employers or internal projects.
</action_safety>

<verification_loop>
- Unit/fixture tests: a person with 10 commits 20 months ago and 1 last month in an area counts 1 (so is excluded at
  minCommits 2); a leaving person with 1 in-window commit gets no row; a reviewer is counted only when Active, non-bot,
  not the leaving person and `review.at > $since`; 07b explicit and title-match counts add up to the combined count;
  every risk code in the web and Python source is one of the three new codes (grep test).
- `.venv/Scripts/python -m pytest -q` (integration tests run against the live FalkorDB at 127.0.0.1).
- Live, read-only: `/api/summary` (expect 25 of 69 with today's window, give or take a day's drift) and
  `/api/departure/{login}` for murali-db, scottsand-db and harperjiang. Time both endpoints before and after; the
  departure endpoint should stay under 1.5 s. If it does not, say which query is slow.
</verification_loop>

<compact_output_contract>
One line per numbered item. Then:
- pytest summary;
- headline (bus factor 1 / reportable) for since = 182, 365 and 730 days;
- for the 15 active people with most in-window commits: login, NO OTHER AUTHOR areas, how many of those have
  reviewerCount 0, ONE OTHER AUTHOR areas, and the component names of the zero-reviewer areas;
- murali-db, scottsand-db, harperjiang: the new departure summary numbers and the top decision with its explicit and
  title-match split;
- endpoint timings before/after;
- anything you could not verify.
</compact_output_contract>
