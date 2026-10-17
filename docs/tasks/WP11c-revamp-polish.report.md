1. **Desktop evidence:** Both views use two columns at ≥1024 px, with a sticky evidence panel beside the results.
2. **Mobile first screen:** Hid the Leave eyebrow and extra paragraph on narrow screens, kept the bus factor link, and removed the duplicate risk-window sentence.
3. **Readable source:** Reformatted all `web/` files with section comments in CSS. Maximum line lengths: `app.js` 120, `graph.js` 111, `index.html` 119, `people-combobox.js` 95, `style.css` 82.
4. **Follow-ups:** Added round-robin suggestions, capped each tool at two, skipped the asked question, and used display names with logins when available.
5. **Leave copy:** Fixed contributor wording and singular/plural grammar, clarified the zero-contributor case, and sorted areas by commits descending.
6. **Refresh summary:** Uses the newest refresh with changes and its watcher observations; hides the line when there is no such refresh. The updated Cypher returns observations attached to each refresh while keeping the observations and refresh collections separate to avoid cross-product duplication.
7. **Ask timings:** Added INFO logs for memory recall, each LLM round, each tool batch, recording, and total time, tagged with a shortened visitor ID.
8. **Departure graph:** Reserves cut-off people and decision nodes before filling the graph cap with BFS nodes.

**Verification:** `.venv/Scripts/python -m pytest -q` — 91 passed. Per-file `node --check` and the graph-cap test passed. The literal `node --check web/*.js` wildcard does not expand in PowerShell, so I checked each JS file individually.

**Layout check:** No headless browser was available. At 1280 px, the CSS gives the 1076 px inner shell 650 px for content, a 28 px gap, and 398 px for evidence. The evidence panel occupies the first grid row beside results, sticks at 16 px, and its canvas is within the first viewport on a standard desktop-height display.

**Commit:** Not created; the workspace’s `.git` directory denied creation of `index.lock`.