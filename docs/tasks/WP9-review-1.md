<review>
Reviewer (Claude Code) ran the live refresh: git pull + GitHub fetch loaded 6 new commits and 8 new PRs in 8.7 s; two
components moved AT RISK -> COVERED and the watcher wrote 4 sensible observations to mem_team. Good. Fix these.
</review>

<fixes>
1. Query numbering: two files use the `15_` prefix and one uses `15z`. Rename so each number is one feature:
   15_refresh_watermarks, 15a_refresh_head_files, 15b_refresh_component_risk; 16_team_write_observation,
   16b_team_recall, 16c_team_record_refresh, 16d_team_list. Update code, tests and docs/QUERIES.md.
2. The refresh summary line "New commits per component" adds up to 37 for 6 commits: it counts file touches. Count
   distinct commits per component (or rename the label to file touches; counting commits is preferred).
3. 14c_mem_recall returns a placeholder correction {source: null, text: null, ts: null} when an entity has no
   corrections (collect over an OPTIONAL MATCH). Collect only non-null corrections. Check 16b for the same pattern.
4. Recall is too big. One earlier departure answer recorded 30+ entities, and recall returns all of them into the first
   user message. Cap it: entities that match the current question first (by key or name), then the most recent; at
   most 8 entities; include changedSinceLastAsked only when it has commits or PRs; drop empty fields. Keep the full data
   available to the UI through /api/memory/{user}. Do not record `(test-resources)` components as entities.
5. Add a test for each of the above.
</fixes>

<verification_loop>
pytest must pass. Show the first user message the agent would send for user reviewer_live and the question
"What changed in kernel since I last asked?" (build it with the real recall, no LLM call), and its length in characters.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; the first user message and its length.
</compact_output_contract>
