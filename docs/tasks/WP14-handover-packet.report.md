# WP14 report

Built by Claude Code on 2026-10-17 at the developer's request (Codex was out of usage), verified live and in the UI.

1. `18_handover_candidates`: candidates are recent authors plus recent reviewers of the area; separate columns
   `reviewedTheirPRs`, `sharedFiles`/`outOf`, `areaCommits`, `areaReviews`, `sharedDecisions`, `toLearn`, each in its
   own WITH stage; plain sort, reviews of the leaving person's PRs first; `$exclude` rows come back last as `skipped`.
   (FalkorDB rejects `list + collect(...)` in one WITH, so list unions are split into two stages.)
2. `18b_handover_reading`: the person's PRs in the area, explicit decision link first, then files here, then newest.
3. `18c_handover_decisions`: decisions linked through PRs or an RFC document in the area, explicit/title-match counts,
   issue and RFC path, participants, and the SUPERSEDED_BY reason from either end.
4. `src/busfactor/handover.py`: why sentence from the columns only, up to 6 template questions each tied to its row,
   skipped candidates with their note, "what changed" against the last saved packet (`18e_handover_activity_since` for
   new work), caveat, Markdown checklist with GitHub links, and `18_handover_graph` evidence (no Commit/File nodes).
5. Team memory: `16e` write availability, `16f` latest availability per person, `16g` save packet, `16h` last saved
   packet. Notes are written as `chat:<visitor>`, so Start over removes them. `BUSFACTOR_TEAM_GRAPH` lets tests and UI
   checks use a throwaway graph. Labels: "Unverified availability note", "Saved handover plan".
6. Agent tools `handover_plan(login, component)` and `mark_unavailable(login, reason)`; prompt says when to use them.
7. API: `GET /api/handover/{login}?component=`, `POST /api/handover/{login}/save`, `POST /api/availability`;
   404 via `17c_active_person` / `17d_component_exists`. Also fixed: Start over failed with "empty key" for a visitor
   who never asked a question, so their team notes were not removed.
8. UI: "Draft handover" on every exposed area card opens the packet under the card; per-candidate "Mark unavailable"
   (inline reason), "Mark available" on skipped people, "Save to team memory", "Copy as Markdown", Markdown view;
   the evidence panel shows the packet graph. No horizontal overflow at 375 px.

pytest: 114 passed (5 new in tests/test_handover.py, including column non-multiplication on a fixture graph);
node tests passed; `scripts/smoke_live.py` passed.

Live packets (since = 365 days), 68-98 ms each. No area has an explicit decision link; title-match decisions exist for
kernel-api/tablefeatures (5), kernel-api/metrics (2), flink/inttest (1), spark/uniform (1), spark/deletionvectors (1).

| login | component | top candidate | why |
|---|---|---|---|
| harperjiang | flink/inttest | scottsand-db | reviewed 2 of 3 PRs here; took part in Catalog-Managed Tables |
| harperjiang | flink/kernel | kaiqijinwow | reviewed 2 of 4 PRs here (tie with murali-db) |
| prakharjain09 | spark/deletionvectors | murali-db | reviewed 6 of 6 PRs here; 1 own commit; 9 reviews here |
| scottsand-db | kernel/kernel-api/tablefeatures | xx-db | reviewed 3 of 3 PRs here; 5 title-match decisions |
| seewishnew | spark/v2/tablemanager | huan233usc | reviewed 5 of 7 PRs here |

Demo pair: **harperjiang + flink/inttest**. It continues the Harper/Flink story; the successor's evidence includes a
shared decision; the reading list starts with "[Flink] Support Catalog-Managed Table with UC"; the decision to
preserve is Catalog-Managed Tables with the reason quoted from issue #4381; marking scottsand-db unavailable moves the
suggestion to kaiqijinwow (1 of 3 PRs reviewed, 1 shared file, 1 own commit) and the packet explains why.
UI walkthrough (throwaway team graph): draft -> save -> mark scottsand-db unavailable -> redraft shows the skip and
"What changed"; the chat agent asked for the same handover called `handover_plan` (91 ms) and honoured the note.
