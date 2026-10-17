<context>
Runs after WP14. Read AGENTS.md, docs/QUERIES.md, src/busfactor/tools.py, src/busfactor/agent/loop.py,
src/busfactor/agent/prompt.py, src/busfactor/handover.py, src/busfactor/api/app.py and web/app.js first.

The organisers' blog post ("How to build an agent that reasons over a graph", wemakedevs.org) lists checks judges look
for. Bus Factor matches it except on the agent side: the web endpoints return 404 for an unknown login
(api/app.py `/api/departure`, `/api/handover`), but the agent tools run their query with whatever the model passes and
an empty result reads like "nothing at risk". Verified live on 17 Oct:
- `departure_impact('harper-jiang')` returns 0 rows; `departure_impact('harperjiang')` returns 22.
- `successor('harperjiang', 'flink/intest')` returns 0 rows (the area is `flink/inttest`, which returns 1).
- `find_entity('harper-jiang')` returns nothing; `find_entity('harper')` and `find_entity('jiang')` find harperjiang.
- `find_entity('flink/intest')` returns nothing, and `find_entity('flink', limit 5)` returns
  `connectors/examples/flink-example/*` before any `flink/*` area.
- `tmarzec` (Tomasz Marzec) is a Person but not Active (last seen 2025-10-14); `ghost` is the only bot.
- Real entities with empty results: `successor('harperjiang', 'kernel/kernel-api')`, `orphaned_decisions('harperjiang')`,
  `why_not('catalog-managed')` (it exists but is accepted, not superseded).
- Graph size: 383 Person (294 Active), 287 Component, 28 Module, 19 Decision, 4,455 File.

This package closes the gap with three checks: resolve names before a tool runs, label empty results, and check the
final reply against the rows the tools returned. Hard rules still hold: every check is a read-only Cypher query in its
own header-commented `.cypher` file; Python only decides what to run and how to label it.
</context>

<task>
1. Name-check queries (new files, read-only, each with the usual three-line header: Answers / Parameters / Shape).
   Reuse `17c_active_person` (login is an Active non-bot person) and `17d_component_exists` (exact Component name).
   Add only what is missing:
   - `17e_person_status.cypher` ($login): any Person with that login, returning login, name, `active` (has the Active
     label), `bot`, `lastSeen`. Run it only when 17c returns no row, to tell "in the graph but not Active" (or a bot)
     from "not in the graph at all".
   - `17f_component_prefix.cypher` ($prefix): how many Components start with the prefix (for `componentPrefix`).
   - `17g_decision_exists.cypher` ($slug): slug, title, status of that Decision.
   - `17h_file_exists.cypher` ($path): the File with exactly that path and whether it exists at HEAD.
   - `17i_module_exists.cypher` ($name): the Module with that name (only needed for `remember_correction` keys).
   - `17j_reply_names.cypher` (no params): the names the reply check looks for, as rows of `kind`, `name`, `alias`:
     non-bot Person logins (alias = display name), Component names that contain `/`, Decision titles (alias = slug).

2. Resolve names before a tool runs (src/busfactor/tools.py). Add a plain mapping from tool to the arguments it checks
   and one function, e.g. `resolve_inputs(name, params, *, graph=None) -> dict | None`, that the agent loop, the
   `/api/tools/{name}` endpoint and the CLI all go through:
   - `login` in departure_impact, departure_files, orphaned_decisions, decision_share, successor, simulate_departure,
     handover_plan, mark_unavailable: 17c; if no row, 17e. Not found -> `not_in_graph`; found but not Active or a bot
     -> `inactive` (with name, lastSeen as a date, bot flag).
   - `component` in successor, handover_plan: 17d. `componentPrefix` (only when non-empty) in departure_impact,
     departure_files: 17f, not found when the count is 0.
   - `slug` in why_not: 17g. `path` in decision_trace: 17h.
   - `key` in remember_correction, by prefix: `person:` -> 17e (inactive people are allowed here: corrections can be
     about former maintainers), `component:` -> 17d, `module:` -> 17i, `decision:` -> 17g.
   Check every argument of the call, not just the first, and report each one. When any argument is `not_in_graph` or
   `inactive`, run nothing else (no main query, no memory write) and return the outcome below.
   Suggestions for a `not_in_graph` value come from `13_find_entity` only, filtered to the expected kind: run it on the
   raw text, then on the text with `-`, `_`, `.` and spaces removed, on each token of 3+ characters split on
   `-_/. `, and for a component or path on its parent prefix with a trailing slash (`flink/`) and its last segment.
   Deduplicate, order by string similarity to the original text (difflib is fine: this only orders graph results),
   and keep 5, each as `{key, label}`. `harper-jiang` must suggest `harperjiang` first and `flink/intest` must
   suggest `flink/inttest` first.
   Route every check query through one small helper keyed by query name so unit tests can fake it without FalkorDB.

3. Outcomes. Every tool call in the agent loop gets an `outcome`:
   - `ok`: the entity checks passed and the tool returned rows;
   - `unknown_entity`: some argument is not in the graph; carry `checks` (arg, value, kind, status, suggestions) and a
     `note`: "Nothing else was run. Use one of the suggestions or ask the user which they meant; this result says
     nothing about risk.";
   - `inactive_person`: the person exists but is not Active (or is a bot); the note names the last-seen date and says
     the departure tools only cover people active in the last 12 months; nothing else was run;
   - `no_qualifying_evidence`: every name checked out (or the tool takes none) and the query returned 0 rows. The note
     says what the query requires, per tool, from a plain dict of one-line threshold texts (for example
     departure_impact: "areas where this person made 2+ non-bulk commits on current files in the last 12 months";
     why_not: "a rejected decision with a SUPERSEDED_BY edge"), and ends: "The graph holds no qualifying evidence for
     this; do not read it as nothing being at risk.". For handover_plan, it applies when the packet has no candidates
     and an empty reading list.
   - errors stay `is_error` tool results as today.
   The model's tool_result JSON gets `outcome`, `checks` (when any) and `note` next to `row_count` and `rows`.
   `unknown_entity`, `inactive_person` and `no_qualifying_evidence` count as successful FalkorDB answers (the existing
   "no successful tool" fallback must not replace an answer like "harper-jiang is not in the graph; did you mean
   harperjiang?"). Calls blocked by a check are left out of the follow-up chip input and of memory entity keys.
   `/api/tools/{name}` returns the same `outcome`, `checks` and `note` fields (200, rows empty) so the no-key starter
   tables can say "Not in the graph" instead of "No matching rows".
   Also replace the inline Cypher string in `/api/departure` with `17c_active_person` (same result), so no Cypher
   lives in Python.

4. System prompt (agent/prompt.py), a few short sentences: on `unknown_entity`, do not answer from that call; retry
   with a suggestion when one is clearly meant, otherwise say the name is not in the graph and offer the suggestions;
   on `inactive_person`, say the person is in the graph but has no activity in the last 12 months (give the date);
   on `no_qualifying_evidence`, say the graph holds no qualifying evidence and name the threshold, never "nothing is
   at risk" or "no impact". Keep the tool-schema budget test passing.

5. Reply check (new src/busfactor/agent/reply_check.py, called at the end of `ask`). Pure function over the final
   answer text, a "seen" text and the 17j names; no rewriting of the answer.
   - Seen text: the question, the first user message (it carries memory and team-memory notes) and every tool_result
     content string the model received in this turn, lower-cased.
   - Names to look for in the answer: PR or issue numbers (`#1234`, `PR 1234`, `PR #1234`, `issue #4381`, GitHub
     `/pull/N` and `/issues/N` URLs; 3+ digits so "#1 candidate" is not one); `@mentions`; 17j logins (skip logins
     shorter than 4 characters; whole-token, case-insensitive, where `-`, `_`, `/`, `.` count as part of the token);
     17j component names; backticked spans that contain `/` and are not URLs (paths or areas); 17j decision titles
     (case-insensitive).
   - A name is found when it appears in the seen text with the same token boundaries; a decision counts as found
     when its title or slug appears; a number when it appears as a whole number.
   - Return `{"checked": <distinct names found in the answer>, "unmatched": [{"kind": "pr"|"person"|"component"|
     "path"|"decision", "text": ...}]}`; add it to the `ask` result as `reply_check`, and log unmatched names with
     `LOGGER.warning("reply_check visitor=%s unmatched=%s", ...)`. If 17j fails (for example a fake graph in tests),
     still check the pattern-based names and log that the catalogue was unavailable; never fail the answer. Skip the
     check for the fixed "could not establish an answer" text.

6. How I know (web/**):
   - Under the answer text, when `reply_check.unmatched` is non-empty, a visible warning (not inside How I know):
     "Not found in this turn's graph results: PR #6189, tdas. Check these before relying on them." Plain words, no
     icon-only signal, readable in light and dark.
   - The How I know summary adds the check: "How I know · 3 graph tool calls · 9 names in the answer checked against
     the results" or "… · 1 name not found in the results".
   - Each call card shows its outcome in words beside the existing "N rows · N ms": OK / Not in the graph / Not active
     / No qualifying evidence / Error, then the note, then for each check one line such as
     "Checked login harper-jiang: not in the graph (17c_active_person, 17e_person_status · 4 ms). Did you mean:
     harperjiang (Hao Jiang)?" The check queries' Cypher goes under the existing "Cypher query" details, labelled with
     the file name. Add check time to the trail only if it is cheap (it is: time it next to the existing `ms`).
   - The no-key readable tables show the note instead of "No matching rows in the current graph." when an outcome
     other than `ok` comes back.
   - Names or "they", never inferred pronouns. Readable at 1280 x 765 and on mobile.

7. Smoke script: `scripts/smoke_live.py` keeps its one live call; also print each tool's outcome and the reply_check
   result. Add docs/QUERIES.md entries for the new query files.
</task>

<action_safety>
Edit only queries/** (new 17e-17j files only; do not change existing queries), src/busfactor/** (tools.py,
agent/loop.py, agent/prompt.py, new agent/reply_check.py, api/app.py, handover.py only if needed), web/**, tests/**,
scripts/smoke_live.py and docs/QUERIES.md. Do not touch README.md, docs/DEMO.md, docs/BLOG.md, docs/PROGRESS.md,
AGENTS.md, CLAUDE.md, docs/PLAN.md or docs/tasks/. Read-only against the live `delta` graph and never write to the live
`mem_team` or any `mem_*` graph (unit tests fake memory; integration tests that write use throwaway graph names).
No live LLM calls (the reviewer runs scripts/smoke_live.py). Do not run git commit. Never mention employers or
internal projects. Do not stop or remove Docker containers you did not start.
If time is short, cut in this order: the module and file checks for remember_correction, then the `/api/tools`
outcome fields. Never cut the outcomes, the suggestions, the reply warning or the tests.
</action_safety>

<verification_loop>
- Unit tests with a faked check helper and ScriptedLLM (no FalkorDB):
  `departure_impact('harper-jiang')` -> `unknown_entity`, main tool function never called, suggestions in the
  tool_result, the scripted final answer kept (not replaced by the "no successful tool" text);
  an inactive person -> `inactive_person` with the last-seen date and no main call;
  `successor('harperjiang', 'flink/intest')` -> `unknown_entity` naming only the component argument;
  a tool returning 0 rows for a known entity -> `no_qualifying_evidence` with that tool's threshold note;
  a tool with rows -> `ok`; `mark_unavailable` for an unknown login writes nothing;
  `remember_correction` with `person:<inactive>` is allowed;
  reply check: an answer naming a PR, a login, a component and a decision that are all in the rows -> no unmatched;
  an answer naming `#6189`, `tdas` and `flink/intest` not in the rows -> exactly those three unmatched;
  "#1 candidate", ordinary words and a 3-letter login do not trigger; a name only in the question is found;
  the 17j failure path still checks PR numbers.
- Existing tests that pass `graph=object()` must stub the check helper rather than skip the checks.
- Live, read-only integration test (marked like the existing ones): the check queries return the expected rows for
  harperjiang, harper-jiang, tmarzec, ghost, flink/inttest, flink/intest, catalog-managed, managed-commit; suggestions
  for `harper-jiang` start with harperjiang and for `flink/intest` with flink/inttest; time one check and 17j.
- `.venv/Scripts/python -m pytest -q`, node UI checks and the schema budget test.
</verification_loop>

<compact_output_contract>
One line per numbered item; the new query files with one line each on what they answer; pytest summary; live timings
for a name check and for 17j; the suggestion lists for harper-jiang, flink/intest and managed-commit; anything you
could not verify.
</compact_output_contract>
