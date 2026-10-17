### Files changed

- API and agent: [app.py](../../src/busfactor/api/app.py), [tools.py](../../src/busfactor/tools.py), [loop.py](../../src/busfactor/agent/loop.py), [memory.py](../../src/busfactor/agent/memory.py), and new [followups.py](../../src/busfactor/agent/followups.py).
- Queries and guide: updated [10b_why_not.cypher](../../queries/10b_why_not.cypher), added [17_people_search.cypher](../../queries/17_people_search.cypher) and [17b_team_delete_visitor_claims.cypher](../../queries/17b_team_delete_visitor_claims.cypher), and documented them in [QUERIES.md](../../docs/QUERIES.md).
- Tests: added [test_api_revamp.py](../../tests/test_api_revamp.py).

Query 17 counts each Active, non-bot person’s distinct recent non-bulk commits, ranking login/name prefixes before contains matches. Query 17b deletes only observations written by the specified visitor and reports how many it removed. The updated 10b query counts later edits connected to the replacement decision; follow-up questions about drift require that count to be positive.

### Verification

`.venv/Scripts/python -m pytest -q`: **90 passed**.

Live TestClient responses against `delta`:

```json
{
  "path": "/api/summary",
  "status": 200,
  "body": {
    "busFactorOne": 42,
    "componentsReported": 87,
    "windowDays": 365,
    "minCommits": 2,
    "minTotal": 5,
    "examples": [
      {"component": "sharing/(core)", "topExpert": "littlegrasscao", "total": 38.0},
      {"component": "kernel/kernel-api/snapshot", "topExpert": "scottsand-db", "total": 37.0},
      {"component": "kernel/kernel-api/test", "topExpert": "scottsand-db", "total": 34.0}
    ],
    "snapshotDate": "2026-10-16",
    "dataWindow": "2 years loaded; risk uses the last 12 months and at least 2 commits"
  }
}
```

```json
{
  "path": "/api/people?q=m&limit=5",
  "status": 200,
  "body": {
    "people": [
      {"login": "murali-db", "name": "Murali Ramanujam", "recentCommits": 85, "lastSeen": 1792103650000},
      {"login": "fwc", "name": "Matthis Gördel", "recentCommits": 14, "lastSeen": 1791999559000},
      {"login": "milastdbx", "name": "Milan Stefanovic", "recentCommits": 9, "lastSeen": 1780473917000},
      {"login": "ilicmarkodb", "name": "Marko Ilić", "recentCommits": 8, "lastSeen": 1783439029000},
      {"login": "mkroll-db", "name": "Marco Kroll", "recentCommits": 6, "lastSeen": 1790878323000}
    ]
  }
}
```

```json
{
  "path": "/api/suggestions",
  "status": 200,
  "body": {
    "suggestions": [
      {"id": "departure", "question": "What does the project lose if Murali Ramanujam (@murali-db) leaves?", "tool": "departure", "params": {"login": "murali-db"}},
      {"id": "successor", "question": "Who could take over sharing/(core) if littlegrasscao left?", "tool": "successor", "params": {"login": "littlegrasscao", "component": "sharing/(core)"}},
      {"id": "superseded-decision", "question": "Why was Managed Commits rejected, and what replaced it?", "tool": "why_not", "params": {"slug": "managed-commits"}},
      {"id": "owners", "question": "Where do the declared CODEOWNERS differ from the people doing the work?", "tool": "declared_vs_actual", "params": {}}
    ]
  }
}
```

**Contract changes:** none. WP11b’s concurrent edits are present in `web/` and `tests/test_api_integration.py`; I did not edit those files.