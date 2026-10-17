<review>
WP13a stopped before its report because Codex hit its usage limit. Claude Code reviewed the working tree on
2026-10-17 at about 16:30 IST.

Verified and accepted:
- pytest: 104 passed.
- Live (TestClient on the new code; same numbers from an independent Cypher check): headline 25 of 69 (since = 365 days);
  18 of 48 at 182 days; 39 of 101 at 730 days. murali-db: 1 NO OTHER AUTHOR (spark-unified/sql, 7 reviewers), 6 ONE
  OTHER AUTHOR. harperjiang: 3 NO OTHER AUTHOR (flink/kernel 5 reviewers, flink/inttest 5, flink/(files) 6), 5 ONE OTHER
  AUTHOR. scottsand-db: 2 NO OTHER AUTHOR (kernel/kernel-api/tablefeatures 16, kernel/kernel-api/metrics 5), 2 ONE
  OTHER AUTHOR. Catalog-Managed Tables split: explicit 1 of 3, title match 42 of 85.
- Timing: /api/summary 81 ms; /api/departure 373-542 ms.
- Queries 05, 05b, 06, 07b, 08, 12, 15b and their graph companions follow the brief; copy and tooltip render as asked.
</review>

<fixes>
1. Focus graph regression. `_focused_departure_graph` now keeps PR nodes and every REVIEWED edge from the impact graph:
   harperjiang's graph has 191 nodes (161 PRs, 183 REVIEWED edges), and the UI shows "60 of 191 nodes" as a ring of tiny
   PR labels, which is the problem WP11d fixed. Revert to Person/Component/Decision nodes only and drop the REVIEWED
   retention. Reviewers stay in the area cards and in "Show full evidence". (WP13b item 2 adds collapsed reviewer edges
   and capped decision PRs properly.) Add a test: the focus graph for a fixture departure has no PR, Commit or File
   nodes and at most 60 nodes.
2. "0/0" decision tile. murali-db's leading decision (Enforce Vacuum Protocol Check) has no explicit links, so the
   "Explicit decision PRs" tile shows 0/0 and the card says "they opened 0 of 0". When `explicitPRs` is 0, the tile shows
   "none" and the card says "No explicitly linked PRs · Title match only: a of b". In 07b wrap the counts in
   `toInteger(...)` (sum() returns 1.0, 42.0, which the agent sees as floats).
3. Retired codes in refresh text. The landing page's refresh line reads "risk changed from AT RISK to COVERED", from
   mem_team observations written on 16 Oct. Also, 15b has no leaving person, so "ONE OTHER AUTHOR" is the wrong word
   for refresh. In refresh.py, write refresh observations in coverage terms ("recent authors changed from 1 to 2+"), and
   where team-memory text is shown, map the retired codes for display (ORPHANED -> no recent author, AT RISK -> one
   recent author). Do not edit or delete stored observations.
</fixes>

<action_safety>
Edit only src/busfactor/api/app.py, src/busfactor/refresh.py, queries/07b_decision_share.cypher, web/app.js and tests.
Same rules as the WP13a brief: no README/PROGRESS/DEMO/BLOG edits, read-only against live graphs, no git commit.
</action_safety>

<verification_loop>
pytest; live focus-graph node counts by label for murali-db, scottsand-db and harperjiang; the murali-db decision
tile text.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; the three focus-graph counts.
</compact_output_contract>
