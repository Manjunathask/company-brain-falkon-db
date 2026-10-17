### Files changed

- [web/index.html](../../web/index.html), [web/app.js](../../web/app.js), [web/style.css](../../web/style.css)
- [web/graph.js](../../web/graph.js), [web/people-combobox.js](../../web/people-combobox.js)
- [tests/test_api_integration.py](../../tests/test_api_integration.py), [tests/js/test_graph_cap.mjs](../../tests/js/test_graph_cap.mjs)

### Verification

- Pytest: **90 passed**
- `node --check`: all three `web/*.js` files passed; graph-cap unit check passed.
- Server smoke check: `/`, `app.js`, `graph.js`, and `people-combobox.js` all returned **200** via curl.

### Reviewer notes

The departure and Ask views now have separate evidence state. The graph cap keeps a BFS-rooted subgraph and only edges whose endpoints remain in it. The picker supports keyboard selection and ignores stale search responses.

The `/api/ask` trace contract provides `row_count`, but not tool result rows. “How I know” shows the count and states when row values are unavailable, while retaining parameters, duration, and Cypher. No files outside the authorized frontend and integration-test scope were edited by this work.