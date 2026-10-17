Implemented WP3.

### Files created or changed

- Added derive queries: [03_derive_knows.cypher](../../queries/03_derive_knows.cypher), [03b_derive_last_seen.cypher](../../queries/03b_derive_last_seen.cypher), [04_derive_works_with.cypher](../../queries/04_derive_works_with.cypher), [04b_derive_participated_pr.cypher](../../queries/04b_derive_participated_pr.cypher), [04c_derive_participated_issue.cypher](../../queries/04c_derive_participated_issue.cypher)
- Added [derive.py](../../src/busfactor/derive.py), [check_assumptions.py](../../scripts/check_assumptions.py), and [test_derive_queries.py](../../tests/test_derive_queries.py).
- Appended the WP3 entry to [PROGRESS.md](../../docs/PROGRESS.md).

The derive CLI uses the requested defaults and flags, reports per-query relationship creation counts and runtimes, and prints the sanity summary. Derived edges and activity labels are refreshed on reruns, and bots are filtered or cleaned from those derived relationships.

### Verification

- `.venv/Scripts/python -m pytest -q`: **17 passed**.
- `git diff --check`: passed.
- FalkorDB was **unreachable at localhost:6379** (connection refused). The derive CLI and assumptions checker could not produce live query results.

### Reviewer checks

- Run the derive CLI and assumptions checker against live FalkorDB to confirm Cypher behavior, algorithm availability, and actual counts; those checks could not run here.
- The participation relationship has one `via` property. When both evidence paths exist, the PR path is retained; review whether that priority suits the intended reporting.
- `docs/tasks/WP4-implements-linking.md` appeared as an untracked file and was left untouched.