## WP6 complete

Added the typed tool registry in [tools.py](../../src/busfactor/tools.py), the copy-based simulator in [whatif.py](../../src/busfactor/whatif.py), the WP6 result and evidence queries, integration coverage, [QUERIES.md](../../docs/QUERIES.md), and a progress entry. The guide covers all 44 query files. No commit was made.

**Tests:** `36 passed`.

**Live checks** (trimmed):

| Tool | Result |
|---|---|
| `find_entity --text catalog` | Found `kernel-spark/catalog` and `decision:catalog-managed` (“Catalog-Managed Tables”). |
| `departure_impact --login huan233usc` | First results include `kernel-spark/(core)` and `.github/(files)`, both `ORPHANED`. |
| `successor --login huan233usc --component kernel-spark/catalog` | `gengliangwang`; 3 shared files out of 3; 4 component commits. |
| `orphaned_decisions --login scottsand-db` | No rows. |
| `decision_trace` | Traced `IcebergCompatMetadataValidatorAndUpdater.java`; results include low-confidence `title-keyword` links. |
| `simulate_departure --login timothyw553` | 290 groups before and after; betweenness rank 3; no former collaborators split into different groups. |
| `bridges` | Top results included `murali-db`, `yumingxuanguo-db`, and `timothyw553`. |

`GRAPH.LIST` was `['delta']` both before and after simulation. The live graph’s node and edge counts also matched: **11,017 nodes and 40,132 edges**. The fixture test separately verifies a 2→3 group split and that the copied source graph remains unchanged.

The live server accepted `CALL db.idx.fulltext.createNodeIndex('Decision', 'title')` and the corresponding PR index. Lookup uses `CALL db.idx.fulltext.queryNodes('Decision', text) YIELD node, score`; the tool returned the Catalog-Managed decision for “catalog”.

The live Timothy simulation did not split a group; the fixture covers that case. Concurrent workspace changes to `pyproject.toml`, `uv.lock`, and `docs/tasks/WP7-agent-and-memory.md` appeared during this work and were left untouched.