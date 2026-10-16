- **Fix 1 — connections:** `db.py` now caches one client per process and exposes `get_graph(name)`; the app, what-if simulator, memory, scripts, tests, and `.env.example` default to `127.0.0.1`. I did not edit `README.md`; the note to add there is that Docker binds IPv4 loopback, while Windows may try IPv6 first for `localhost`.
- **Fix 2 — concurrent simulations:** What-if graph names include a random suffix; the `GRAPH.COPY` command is serialized, then queryability is polled every 50 ms for up to 5 seconds. The concurrent same-login integration test passed and confirmed cleanup.
- **Fix 3 — readable tool results:** `10_decision_trace.cypher` now returns file, commit, PR, decision, and issue properties alongside the path. I checked the other tool result queries; none had the same paths-only result issue.
- **Fix 4 — test-resource noise:** `05b`, `06`, and `06b` exclude component names ending in `/(test-resources)` by default; `includeTestResources` opts them back in.
- **Fix 5 — departure scope:** `06` and `06b` accept `componentPrefix` (for example, `spark/v2`); `06` now orders orphaned and at-risk components first, then by departing commit count.
- **Fix 6 — parallel tools:** Each agent turn runs tool calls concurrently with up to 6 workers, while preserving call order in one tool-result message.
- **Fix 7 — agent defaults:** The default remains `claude-sonnet-5-5` at medium effort.
- **Fix 8 — entity search:** `13_find_entity.cypher` matches partial logins and ranks exact login, login prefix, then other matches.

The departure queries apply the component prefix and test-resource filters before aggregating evidence, so the returned counts match the requested scope. The decision trace returns readable properties beside its path; entity search assigns higher scores to exact and prefix login matches.

**Verification:** `pytest -q` — **54 passed**. The concurrent-simulation integration test passed.

**CLI timing:** `departure_impact --login scottsand-db` took **2.63 s before** and **0.60 s after**.

**Decision trace:** For `kernel/kernel-api/src/main/java/io/delta/kernel/internal/icebergcompat/IcebergCompatMetadataValidatorAndUpdater.java`, the query returned:

| Commit SHA | PR | Decision | Status | Confidence / via | Issue |
|---|---:|---|---|---|---:|
| `86b84c4da62dee5a02a2d26ecddd6e29c8db3289` | 5231 | IcebergCompatV3 | proposed | low / title-keyword | 4574 |
| `7e5b26f595ddfa48f8f4afbe0c2eeb67b7aadbd7` | 4595 | IcebergCompatV3 | proposed | low / title-keyword | 4574 |
| `0d1600e55075941c0a6f7317fc86c194c6ae03aa` | 4732 | IcebergCompatV3 | proposed | low / title-keyword | 4574 |
| `a76fcfe258bc9e0252f18e3675becb9f096f09db` | 4291 | IcebergWriterCompatV1 | proposed | low / title-keyword | 4284 |

An earlier full-suite run briefly failed a WP8 focus-graph assertion; the final full run passed.