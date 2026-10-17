# Bus Factor UI/UX revamp — plan (reviewed by Codex GPT-6-Astra, medium)

## Context

The app works but is built for its builders. A newcomer (a judge, a new Delta contributor, a manager) lands on a page
that asks for a GitHub login, shows internal "watcher" notes, an empty graph canvas, and a chat box with no hint of
what to ask. The departure tab needs an exact login. Two visible bugs undermine trust: the evidence graph can show
"60 nodes · 0 edges" as a grid, and "People cut off" looks empty. Goal for Saturday 17 Oct: a newcomer sees the
problem in one number, picks a maintainer from a ranked list or clicks a named starter question, and gets an answer with
readable evidence — no login, no setup questions. Scope was cut to fit one day after the Codex review.

Decisions taken with the developer: light intro landing **plus one headline number from query 5**; Tab-to-complete kept
in its simple form; simple progress (no streaming).

## Root causes of the two bugs (from the code map and the Codex review)

- "60 nodes · 0 edges": the right-hand evidence panel is shared by both tabs and is not redrawn on tab switch
  (web/app.js:126). The person search and the tool box run `find_entity`, whose evidence query returns nodes only
  (queries/13_find_entity_graph.cypher), and `capGraph` keeps the *last* 60 nodes (web/app.js:30). `_merge_graph`
  (src/busfactor/agent/loop.py:76) keeps first-seen order, so in chat the departing person (seen first) is also cut and
  all its edges vanish. The departure `focus_graph` itself is fine (API: 49 nodes, 84 edges).
- "People cut off" names: rendered, but inside a `<details>` that is collapsed by default with its disclosure marker
  hidden by CSS (web/app.js:149, web/style.css:1).

## Scope

**Must**
1. Fix evidence: each view (Ask answer, Leave result) owns its graph; switching tabs redraws that view's graph; entity
   search never draws into the evidence panel; the cap keeps a connected subgraph (start from the answer's main
   entities — departing person, traced file, decision — expand by BFS, keep edges between kept nodes) and says what was
   omitted. Show cut-off names, decisions and file groups open by default with counts in the headings.
2. No login: the browser creates an anonymous visitor id (`v_` + 32 hex from `crypto.randomUUID()` without hyphens,
   kept in localStorage; in-memory fallback if storage is blocked) and sends it as `user`. Remove the login field.
3. Landing (light intro, top of the Leave tab, which becomes the default view): one sentence on what this is; the
   **headline number** — "42 of 87 active code areas in Delta Lake have a bus factor of 1: one person wrote at least
   half of their commits in the last 12 months." (computed live, never hard-coded); the people picker; three named
   starter questions; the disclaimer "Estimated from public repository activity; it does not measure everything a
   person knows."; snapshot date and data window ("2 years loaded; risk uses the last 12 months, ≥ 2 commits").
4. People picker (accessible combobox, ARIA 1.2): on focus lists the top 10 maintainers by non-bulk commits in the
   window (initials, name, @login, commit count); typing filters by prefix on login or name, then contains, ranked by
   commits ("m" → Murali Ramanujam, Matthis Gördel, Milan Stefanovic, …); ↑/↓/Enter/Esc, touch; stale responses ignored;
   loading, no-match and unknown-person states. Selecting runs the simulation and sets `#leave/<login>`.
5. Leave result copy: one plain sentence ("If Murali Ramanujam left: 5 code areas would have no other active
   contributor with ≥ 2 recent commits, 11 would rely on one remaining person, 43 current files would have no other recent
   editor, and 3 people would lose their link to the main collaboration network.") — numbers from the response; metric
   cards with short "what this means" tooltips (bus factor, ORPHANED, AT RISK, bridge rank, cut off = loses its only
   link in the modelled who-edits-the-same-files network, decision share = opened X of Y PRs linked to the decision).
   Successor shown for the top area by default with a "show successors for this area" action on every exposed area
   (calls the existing successor tool on demand).
6. Ask tab: empty state with a greeting and 4 named suggestion chips from live data; the question appears immediately
   with a "Querying the graph…" indicator, Enter sends, Shift+Enter new line, retryable errors; answer rendered as
   sanitised markdown with a plain-text fallback; "How I know" keeps tool, params, rows, ms and Cypher (copy button).
7. **Follow-up chips (up to 4) under each answer**, built in the agent loop from the structured rows of successful tool
   calls (not from prose), so every premise is backed by the graph; each is a complete question with names filled in
   (the agent has no conversation memory between questions, src/busfactor/agent/loop.py:158). Clicking one asks it in
   the same chat view.
8. Chat disabled (no API key): a "Try without AI" route stays obvious — Leave view, starter questions that map to tools
   run the tool directly; operator instructions live in the README, not in the judge's face.
9. Keyboard-only and 390 px flows; on mobile the explanation and next action come before the graph; contrast AA;
   `aria-live` for answers; risk shown as text badges, not colour only.

**Should**
- Tab-to-complete (simple): grey ghost text from the visible suggestion list when the typed text is a prefix of one; Tab
  accepts, Esc dismisses; with no ghost text Tab moves focus normally.
- Hash links `#ask`, `#leave/<login>`; graph fit/reset/zoom; readable node details; an "Evidence as text" list under the
  graph (accessibility and CDN failure fallback); source links to GitHub for PRs, issues, commits and files (file links
  at the snapshot HEAD sha).
- "Start over" in a small history menu: deletes this visitor's `mem_<id>` and their team claims; ignores in-flight
  answers for a deleted id.
- Team memory moves out of the Ask column into a compact "Recent changes in the repo" line on the landing.

**Could (only if time remains)**: Overview insight cards, live tool-step streaming, `@` mentions, entity chips in
answer prose, full ES-module split of app.js.

## Backend changes (Codex WP11a)
- `GET /api/summary` → `{busFactorOne, componentsReported, windowDays, minCommits, examples:[{component, topExpert,
  total}], snapshotDate, dataWindow}`; reuses `tools.bus_factor_component()` (query 05b) — one query.
- `GET /api/people?q=&limit=10` → `[{login, name, recentCommits, lastSeen}]`; new `queries/17_people_search.cypher`
  (Active, non-bot, non-bulk commits since $since; prefix on login or name first, then contains; empty q = top).
- `GET /api/suggestions` → named starter questions from live data (top maintainer from 17, the busiest bus-factor-1
  component and its expert from 05b, the superseded decision via 10b, declared vs actual owners).
- `AgentAnswer.followups` from new `src/busfactor/agent/followups.py`: one template table keyed by tool name, fed with
  the rows the loop already holds (src/busfactor/agent/loop.py:207), deduplicated, max 4, only from successful calls.
- `GET /api/departure/{login}` unchanged in shape; add `summary` counts used by the sentence; 404 with a friendly
  message for unknown people.
- Anonymous ids: accept `v_[0-9a-f]{32}` alongside logins in memory naming (src/busfactor/agent/memory.py:12);
  `DELETE /api/memory/{user}` for Start over (that graph plus that visitor's team claims).
- Plain-English tool labels in one table in tools.py (used by "How I know").

## Frontend changes (Codex WP11b, runs in parallel on web/ only)
- web/index.html: two tabs, "What if someone leaves?" (default, with the light intro) and "Ask"; remove the login field
  and the static suggestions; evidence panel per view.
- web/app.js: extract the graph code and the people combobox into `web/graph.js` and `web/people-combobox.js` (ES
  modules); keep the rest in app.js; per-view evidence state; connected-subgraph cap; markdown via pinned cdnjs
  `marked` + `DOMPurify`; follow-up chips; ghost-text Tab; request guards.
- web/style.css: design tokens (type scale, spacing, colours), disclosure markers visible, focus rings, mobile order.
- Update tests that assert literal strings in app.js (tests/test_api_integration.py:72) and the `DEPARTURE_FIELDS`
  contract.

## Delivery
WP11a (backend) and WP11b (frontend) run as two Codex sessions on disjoint files against the JSON contract above;
README/PROGRESS edits by the reviewer. WP11c: browser walkthrough fixes. Then review gate, live smoke, Docker judge path
on a fresh volume, push.

## Verification
- pytest: summary count matches 05b; people ranking and prefix ("m" puts murali-db first by commits; name-prefix hits
  like Matthis Gördel); suggestions are named; follow-ups per tool only reference entities in the rows; unknown person
  → 404 message; visitor-id validation; Start over deletes only that visitor's graph and claims; all existing tests.
- `scripts/smoke_live.py` and one live question through the UI.
- Browser walkthrough in the user's Chrome (Claude in Chrome) and the built-in browser at 1280 px and 390 px: first
  visit shows the headline number and top maintainers with no input; "m" filters; Murali's result shows the sentence,
  open cut-off names, and a departure graph with edges and the person in the centre; switching tabs keeps each view's
  graph; Tab completes a suggestion; follow-up chips ask a new question; keyboard-only Leave flow; no-key mode.
- Docker judge path on a fresh volume, review gate (secrets, employer terms), push to GitHub.
