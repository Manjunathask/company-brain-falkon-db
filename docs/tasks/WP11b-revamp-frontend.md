<task>
You are implementing WP11b, the frontend half of the UX revamp of "Bus Factor". Read AGENTS.md, the approved plan
docs/tasks/WP11-ux-revamp-plan.md and its review docs/tasks/WP11-plan-review-codex-astra.md, then web/index.html,
web/app.js, web/style.css and src/busfactor/api/app.py. Use `.venv/Scripts/python` for tests.

A second Codex session (WP11a) is changing the backend at the same time. Touch ONLY web/** and
tests/test_api_integration.py. Do not edit src/, queries/, README.md or docs/PROGRESS.md.

Audience: a newcomer (a judge, a new Delta contributor) who knows nothing about the project. No login, value before
input, every number explained in plain words.

Backend contract (being built now by WP11a; code against it, handle its absence gracefully while testing):
- GET /api/summary -> {busFactorOne, componentsReported, windowDays, minCommits, minTotal, examples:[{component,
  topExpert, total}], snapshotDate, dataWindow}
- GET /api/people?q=&limit=10 -> {people:[{login, name, recentCommits, lastSeen}]}
- GET /api/suggestions -> {suggestions:[{id, question, tool?, params?}]}
- POST /api/ask {question, user, sessionId} -> AgentAnswer {answer, tool_calls:[{tool, label, params, cypher,
  row_count, ms}], graph, entities, followups:[string], memory_recall, team_memory, stop_reason}; 503 when chat is
  disabled (no API key).
- GET /api/departure/{login} -> existing fields + summary:{name, orphaned, atRisk, orphanedFiles, cutOff,
  mainGroupBefore, mainGroupAfter, bridgeRank}; 404 {detail} for unknown people.
- POST /api/tools/{name} {params} -> {rows, cypher, graph, ...} (unchanged); GET /api/team (unchanged);
  GET /api/memory/{user}; DELETE /api/memory/{user}.

Build (plan items 1-9 and the Should list):
1. Layout: header with product name, the one-line description "Who holds the knowledge in Delta Lake, and what breaks
   if they leave", and a dataset chip (snapshot date + data window from /api/summary) with an "About the data" popover
   (sources, exclusions: bots, bulk commits > 100 files, deleted files; the disclaimer). Remove the raw node/edge counts
   from the header (move them into the popover).
2. Two tabs, deep-linkable: "What if someone leaves?" (default, `#leave`, `#leave/<login>`) and "Ask" (`#ask`).
3. Leave view landing (light intro): one sentence on what this is; the headline number from /api/summary rendered as
   "<busFactorOne> of <componentsReported> active code areas in Delta Lake have a bus factor of 1: one person wrote at
   least half of their commits in the last 12 months." with a "what is a bus factor?" tooltip; the people picker;
   three starter chips from /api/suggestions; the disclaimer "Estimated from public repository activity; it does not
   measure everything a person knows."; a compact "Recent changes in the repo" line from /api/team (human wording).
4. People picker in a new web/people-combobox.js (ES module, ARIA 1.2 combobox with listbox): on focus shows the top 10
   (initials avatar, name, @login, "N recent commits"); typing filters via /api/people?q= with a 150 ms debounce;
   ↑/↓/Enter/Esc/Home/End, mouse and touch; aria-activedescendant; ignore stale responses; states for loading, no match,
   API error. Selecting runs the simulation and sets #leave/<login>.
5. Leave result: the summary sentence built from `summary` ("If <name> left: <orphaned> code areas would have no other
   active contributor with at least 2 recent commits, <atRisk> would rely on one remaining person, <orphanedFiles>
   current files would have no other recent editor, and <cutOff> people would lose their link to the main
   collaboration network."), metric cards with "what this means" tooltips (bus factor, ORPHANED, AT RISK, bridge rank,
   cut off, decision share = opened X of Y PRs linked to the decision). Sections open by default with counts in the
   headings: areas with no expert left, areas relying on one person (show who), decisions they carry, people cut off,
   files only they edited (this one may start collapsed, with a visible chevron). Every exposed area gets
   "Show successors" (POST /api/tools/successor on demand) and "Ask about this" (switches to Ask with the question
   prefilled). Unknown person -> friendly message.
6. Ask view: no login field. Visitor id: `v_` + crypto.randomUUID() without hyphens, stored in localStorage
   (in-memory fallback). Empty state: a short greeting and 4 suggestion chips from /api/suggestions (a chip with a tool
   runs that tool directly when chat is disabled). Composer: auto-growing textarea, Enter sends, Shift+Enter new line;
   ghost-text Tab completion only from the visible suggestions when the typed text is a case-insensitive prefix of one
   (Tab accepts, Esc dismisses; otherwise Tab moves focus). On send: append the question at once plus a
   "Querying the graph…" indicator with aria-live; on error show a retry button. Answer: markdown rendered with pinned
   cdnjs `marked` and `DOMPurify` (pick versions you know exist and are at least 2 weeks old; fall back to textContent if
   either fails to load). "How I know": each tool call with its plain-English label, params, rows, ms, Cypher in a
   <pre> with a copy button. Follow-up chips (answer.followups) under each answer; clicking asks that question in the
   same chat. Chat disabled (503): a calm notice "Chat needs an Anthropic API key on the server; you can still use the
   departure simulator and the suggested questions." and keep suggestions usable.
   Returning visitors: if /api/memory/<visitor> has recall, a quiet banner "Welcome back — since you last asked about
   <entity>, <n> new commits landed." A small "Start over" link calls DELETE /api/memory/<visitor> and makes a new id.
7. Evidence graph in a new web/graph.js (ES module): each view keeps its own evidence state; switching tabs redraws that
   view's graph; entity/people searches never draw into the panel; a connected-subgraph cap: start from the main
   entities (departing person = focusRole "departing"; for chat, nodes from the first tool call's params such as login,
   path, slug), BFS outward, keep at most 60 nodes and every edge between kept nodes, and show "showing N of M nodes".
   Layouts: departure = concentric with the person in the centre; chat = breadthfirst from the main entity when it
   exists, else cose. Short labels (login, last path segment, PR #, decision title truncated to 28 chars), full text in
   the details card. Fit/reset/zoom buttons. "Evidence as text" list under the canvas (paths as readable lines) that
   also works if Cytoscape fails to load. Risk colours with text badges. Links to GitHub for PR, issue, commit and file
   nodes (https://github.com/delta-io/delta/pull/N, /issues/N, /commit/SHA, /blob/HEAD/<path>).
8. Accessibility and responsive: visible focus rings, disclosure markers visible, AA contrast, prefers-reduced-motion,
   at 390 px the explanation and next action come before the graph. Design tokens at the top of style.css (type scale,
   spacing, colours). No external fonts.
9. Load app.js and modules with `type="module"` and a `?v=` query string (keep the server's no-cache headers).
10. Update tests/test_api_integration.py: replace the literal-string assertions on app.js with assertions that fit the new
    code (e.g. graph.js exports a cap that keeps edges between kept nodes, departure layout is concentric), keep the
    DEPARTURE_FIELDS contract check in sync, and add a check that index.html loads the module scripts. Add a tiny JS
    unit check runnable with `node` (no npm install) for the cap function in web/graph.js, e.g.
    tests/js/test_graph_cap.mjs, and call it from a pytest test that skips if node is missing.
</task>

<action_safety>
Stay inside web/** and tests/test_api_integration.py (plus the new tests/js/ file and its pytest wrapper in
tests/test_api_integration.py). No build step, no npm packages. Do not run git commit. No live LLM calls. Never send
secrets to the browser.
</action_safety>

<verification_loop>
`node --check` every web/*.js; `.venv/Scripts/python -m pytest -q` (the backend endpoints may still be in progress in
WP11a; if a failure is only because an endpoint is missing, report it). Start the server
(`.venv/Scripts/python -m busfactor.api`) and fetch / and each module with curl to confirm they are served.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; node checks; anything in the contract you could not use; decisions for the reviewer.
</compact_output_contract>
