# WP13a report

Codex implemented items 1-8 and their tests, then stopped at its usage limit before writing this report. Claude Code
reviewed the work (docs/tasks/WP13a-review-1.md), made the three review fixes, and verified it live on 2026-10-17.

1. Windowed counts: 05, 05b, 06, 08 (`theirCommits`), 12 and 15b count distinct in-window, non-bulk commits on current
   files from AUTHORED/TOUCHED; KNOWS keeps its all-history `commits`.
2. The leaving person needs `$minCommits` in-window commits for an area to be reported.
3. Risk codes: `NO OTHER AUTHOR`, `ONE OTHER AUTHOR`, `COVERED` everywhere; guarded by tests/test_risk_codes.py.
   Refresh (15b) has no leaving person, so it returns `recentAuthors` and refresh text reads "recent authors changed
   from 1 to 2+"; older stored observations are shown in the same terms (team_memory.display_text).
4. 06 returns `reviewers` (up to 5) and `reviewerCount`; the departure summary has `noOtherAuthor`,
   `noOtherAuthorOrReviewer`, `oneOtherAuthor`.
5. 05/05b return `countedExperts`; the graph companions draw exactly those people. 06_graph draws the leaving and
   remaining authors and up to 3 reviewed PRs per listed reviewer. The departure focus graph keeps Person, Component and
   Decision nodes only (reviewer PRs made it a 191-node ring); reviewers are on the area cards.
6. 07b returns explicit and title-match counts (integers); the tile shows "none" when a decision has no explicit links.
7. Copy updated (tooltip, data window, Leave sentence, sections, area and decision cards, agent prompt).
8. docs/QUERIES.md updated for every changed query.

pytest: 105 passed; node tests/js/test_graph_cap.mjs passed.

Headline (bus factor 1 / reportable): 182 days 18 of 48; 365 days **25 of 69**; 730 days 39 of 101 (was 42 of 87).

Live departures (365 days):

| login | NO OTHER AUTHOR | of which no reviewer | ONE OTHER AUTHOR | top decision (explicit · title match) | focus graph |
|---|---|---|---|---|---|
| murali-db | 1 (spark-unified/sql, 7 reviewers) | 0 | 6 | Enforce Vacuum Protocol Check (none · 1 of 3) | 17 nodes |
| scottsand-db | 2 (kernel-api/tablefeatures 16, kernel-api/metrics 5) | 0 | 2 | Catalog-Managed Tables (1 of 3 · 42 of 85) | 24 nodes |
| harperjiang | 3 (flink/kernel 5, flink/inttest 5, flink/(files) 6) | 0 | 5 | IcebergCompatV3 (2 of 3 · 3 of 11) | 20 nodes |

Scouting, top 15 active people by in-window commits (NO OTHER AUTHOR / no reviewer / ONE OTHER AUTHOR):
murali-db 1/0/6, timothyw553 2/0/3, huan233usc 1/0/1, porridgeswim 1/0/0, harperjiang 3/0/5, prakharjain09 2/0/1,
seewishnew 4/0/2, yili-db 1/0/0, zikangh 0/0/0, openinx 0/0/2, chengjix 3/0/3, ctring 0/0/0, geraintcjy 1/0/0,
philplato 0/0/0, haosun1993 0/0/1. No top-15 single-author area is unreviewed. Demo hero: harperjiang (Flink).

Timing: /api/summary 82 ms; /api/departure 359-498 ms.
