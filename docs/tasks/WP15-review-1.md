# WP15 review 1 (Claude Code)

Codex (gpt-6-astra, high) ran the brief and stopped at its usage limit after writing the code and tests but before
its report, so there is no `WP15-name-checks.report.md`. This file records the review instead.

## What Codex delivered

- Queries 17e–17j, each with a three-line header.
- `tools.resolve_inputs` and `tools.run_tool`: every entity argument is checked (17c, then 17e for people; 17d, 17f,
  17g, 17h, 17i). A miss runs nothing else. Suggestions come from `13_find_entity` over the raw text, separators
  removed, tokens, and the parent prefix, ordered by string similarity. Outcomes are `ok`, `unknown_entity`,
  `inactive_person` and `no_qualifying_evidence`, with a per-tool threshold note. The agent loop, `/api/tools/{name}`
  and the CLI all go through `run_tool`; `/api/departure` now uses `17c_active_person` instead of inline Cypher.
- `agent/reply_check.py`: numbers, `@mentions`, 17j logins (4+ characters), areas, backticked paths and decision
  titles in the final answer are compared with the question, the first user message and every tool_result string
  of the turn. Unmatched names are logged and returned as `reply_check`; the answer is not rewritten.
- System prompt rules for the three outcomes; How I know shows the outcome, the note, one line per name check (with
  query names and time, plus suggestions) and the check queries' Cypher; the reply warning sits under the answer.
- 26 unit tests in `tests/test_name_checks.py` (faked check helper, ScriptedLLM) and a live read-only test in
  `tests/test_name_checks_integration.py`; existing agent tests stub the checks.

## Fixes in review

- Numbers in the reply warning were labelled "PR #4381" even when the text said "issue #4381"; now "#4381".
- An empty `find_entity` search got the risk-threshold note ("do not read it as nothing being at risk"); it now says
  no graph entity matches and suggests trying part of the name (`EMPTY_NOTES`), with a test.
- The How I know summary said "0 names in the answer checked" when the answer had no names; it now says nothing then.
- docs/QUERIES.md entries for 17c–17j rewritten to say who calls each check and why.

## Checks

- `pytest`: 154 passed. JS syntax check and `tests/js/test_graph_cap.mjs` pass.
- Live: 17c 1.9 ms, 17j 9.1 ms (687 names). Suggestions: `harper-jiang` → harperjiang, leoojiang;
  `flink/intest` → flink/inttest first; `managed-commit` → managed-commits first.
- False-positive scan: `check_reply` over 17 past answers and docs (docs/eval, README, BLOG) detected only real
  logins and decision titles, no ordinary words.
- `scripts/smoke_live.py`: passed (groups: ok, 8.3 s).
- Browser (built-in, 1280 x 800): asked "What does the project lose if harper-jiang leaves?". The first
  `departure_impact` call was Not in the graph with "Did you mean: harperjiang (Hao Jiang), leoojiang?" and "Main query
  was not run"; the agent said harper-jiang is not in the graph and answered for harperjiang, saying so; the empty
  `orphaned_decisions` result was reported as no qualifying evidence, "That doesn't mean there is no risk"; 31 names in
  the answer checked, none unmatched; 20.8 s. A stubbed response (no model call) showed the warning under the answer
  with three unmatched names; no horizontal overflow at 1280 or 375 px.

## Not done / follow-ups

- At 375 px the existing seven-column `decision_share` table is 47 px wider than its card (WP13b layout, not WP15).
- Display names (e.g. "Hao Jiang") are not reply-checked, only logins; checking names would flag correct answers
  whose rows carry only logins.
