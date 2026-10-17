Implemented WP8 without committing.

**Files changed:** [app.py](../../src/busfactor/api/app.py), [__main__.py](../../src/busfactor/api/__main__.py), [index.html](../../web/index.html), [app.js](../../web/app.js), [style.css](../../web/style.css), [test_api_integration.py](../../tests/test_api_integration.py), [conftest.py](../../tests/conftest.py), [loop.py](../../src/busfactor/agent/loop.py), [graphjson.py](../../src/busfactor/graphjson.py), [README.md](../../README.md), and [PROGRESS.md](../../docs/PROGRESS.md).

**Verification:** `50 passed in 34.41s`. The app served its static page and JavaScript. No live LLM call was made.

Health endpoint:

```json
{"ok":true,"graph":"delta","nodes":11017,"edges":39797,"agent_model":"claude-sonnet-5-5"}
```

Trimmed departure response:

```json
{
  "simulation": {
    "login": "murali-db",
    "mainGroupBefore": 91,
    "mainGroupAfter": 87,
    "cutOff": ["chenwang-databricks", "dillitz", "ni-mi"],
    "directCollaborators": 60,
    "betweennessRank": 1,
    "nonSingletonGroupsBefore": 1,
    "nonSingletonGroupsAfter": 1
  },
  "top_orphaned_component": "spark-unified/sql",
  "orphaned_components": [
    "spark-unified/sql",
    "build/(files)",
    "kernel/kernel-api/exceptions",
    "spark-unified/spark-4.0-4.1",
    "spark/metering"
  ],
  "orphaned_file_groups": 18,
  "decision_share": [{
    "decision": "Enforce Vacuum Protocol Check",
    "theirPRs": 1,
    "totalPRs": 3,
    "otherOpeners": [{"login": "timothyw553", "prs": 2}]
  }],
  "successors": [
    {"successor": "huan233usc", "sharedFiles": 1, "outOf": 1, "theirCommits": 1},
    {"successor": "johanl-db", "sharedFiles": 1, "outOf": 1, "theirCommits": 1},
    {"successor": "vitaliili-db", "sharedFiles": 1, "outOf": 1, "theirCommits": 1},
    {"successor": "zikangh", "sharedFiles": 1, "outOf": 1, "theirCommits": 1}
  ],
  "graph": {"nodes": 199, "edges": 560}
}
```

**Reviewer notes:** `/api/tools` lists callable graph tools with schemas; the memory-only correction tool is excluded there because it requires user-scoped memory context. Cytoscape.js is pinned to version 3.30.4 on cdnjs, so the graph canvas depends on the browser reaching that CDN.