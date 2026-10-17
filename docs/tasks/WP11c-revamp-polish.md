<review>
Reviewer (Claude Code) walked through the revamp in Chrome (desktop) and the built-in browser (375 px mobile and 1280 px
emulation). What works: headline number (42 of 87), people combobox (focus lists top 10; "m" -> Murali Ramanujam,
Matthis Gördel, Milan Stefanovic; ArrowDown + Enter runs the simulation and sets #leave/murali-db), the departure
sentence, sections open with counts, focus graph with 84 links, Show successors, Ask without a login, named
suggestion chips, Tab completion ("Why was" -> full question, focus stays), question shown immediately with
"Querying the graph…", grounded answer with one valid follow-up, no console errors, no horizontal overflow on mobile.
WP11a and WP11b are otherwise accepted. This package fixes what the walkthrough found. You may edit src/, queries/, web/
and tests/; not README.md or docs/PROGRESS.md.
</review>

<fixes>
1. Desktop layout (high). At 1280 px both views are a single column and the evidence graph starts about 4,500 px down
   (Leave) or below the chat (Ask). At >= 1024 px use two columns per view: content on the left (about 600-680 px),
   the evidence panel on the right, `position: sticky; top: 16px; max-height: calc(100vh - 32px)` with the canvas
   filling it, so the graph stays visible next to the results or the latest answer. Below 1024 px keep the single
   column with content first, and add a small "Jump to the evidence graph" link after the summary sentence / answer.
2. Mobile first screen. At 375 x 812 the picker starts at 813 px, just below the fold. On narrow screens shorten the
   hero (drop the eyebrow and the extra paragraph, keep one short heading), so the headline number and the picker are
   both visible without scrolling. Remove the duplicated data-window sentence under the headline (the header chip
   already says it); keep the "What is a bus factor?" link.
3. Readable source (hard rule 5: the developer must explain everything). web/app.js has lines up to 1,231 characters
   and web/style.css up to 3,179; graph.js and people-combobox.js are dense too. Reformat all web/*.js, style.css and
   index.html: one statement per line, normal indentation, a short comment above each non-obvious function, CSS one
   declaration per line grouped by section with comments. No behaviour change; keep tests green.
4. Follow-up variety. build_followups (src/busfactor/agent/followups.py) takes rows tool by tool, so a departure answer
   can yield four near-identical "Who could take over X if Y left?" chips. Round-robin across tools (at most 2 per tool,
   first pass one per tool), skip a chip equal to the question just asked, and use the person's display name with the
   login when the rows have it ("Murali Ramanujam (@murali-db)"). Update tests.
5. Copy fixes in the Leave view: "@Murali Ramanujam contributed 18 recent commits" -> "Murali Ramanujam (@murali-db)
   wrote 18 recent commits here"; plurals ("1 recent commit"); "0 other active contributors remain: none." -> "No other
   active contributor with at least 2 recent commits."; order rows within each section by their commits, descending.
6. "Recent changes in the repo: 0 new commits and 0 new pull requests in the latest refresh." comes from the newest
   RefreshRun, which was a dry run. Use the newest refresh that found changes plus the watcher observations (e.g.
   "Last refresh (16 Oct): 6 new commits, 8 PRs; spark/v2/tablemanager is no longer at risk."); hide the line when there
   is none.
7. Diagnose slow answers: one browser ask took 50 s while the same question took 6.9 s via curl. Log per-phase timings
   for /api/ask at INFO (memory recall, each LLM round, each tool batch, recording) with the request's visitor id
   shortened, so a slow answer can be explained from the server log.
8. Departure graph: "showing 47 of 49 nodes" hides cut-off people who are not direct collaborators. Always keep the
   departing person's cut-off people and the decision nodes in the departure graph (they are the story), then fill
   with BFS up to the cap.
</fixes>

<verification_loop>
`.venv/Scripts/python -m pytest -q` and `node --check web/*.js` must pass. Report the max line length of every web/
file after reformatting. Measure, with a headless check if you have one (otherwise describe the CSS), that at 1280 px
the evidence canvas top is within the first viewport next to the results.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; max line lengths; anything you could not verify.
</compact_output_contract>
