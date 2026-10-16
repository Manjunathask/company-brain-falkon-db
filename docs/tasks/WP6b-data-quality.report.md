## WP6b complete

The full live pipeline (`load all` → `link_decisions` → `derive`) ran successfully. **38 tests passed**, including the `bf_test` integration tests for deleted-file filtering, bulk commits remaining traceable, and decision share. No commit was created.

Files changed: `git_log.py`, `derive.py`, `tools.py`; load, derive, departure, successor, and decision-share Cypher files; `docs/QUERIES.md`, `docs/PROGRESS.md`; and the derive and integration tests.

## Scouting table

Top 15 authors by commits in the loaded two-year history. Risk metrics use the tools’ defaults: a one-year activity window and `minCommits=2`; decision share uses `minShare=0.3` and `minConfidence=low`.

| Login | Commits | Orphaned files | ORPHANED components | AT RISK components | Decision-share rows |
|---|---:|---:|---:|---:|---:|
| huan233usc | 125 | 33 | 8 | 6 | 0 |
| scottsand-db | 119 | 34 | 5 | 8 | 1 |
| allisonport-db | 103 | 60 | 8 | 14 | 1 |
| murali-db | 92 | 43 | 5 | 11 | 1 |
| harperjiang | 80 | 81 | 7 | 4 | 1 |
| ctring | 74 | 26 | 0 | 1 | 0 |
| timothyw553 | 67 | 40 | 8 | 7 | 1 |
| porridgeswim | 55 | 8 | 2 | 2 | 0 |
| chengjix | 48 | 14 | 4 | 5 | 0 |
| prakharjain09 | 48 | 24 | 3 | 2 | 0 |
| xzhseh | 47 | 4 | 1 | 0 | 0 |
| johanl-db | 42 | 17 | 2 | 3 | 1 |
| seewishnew | 41 | 38 | 8 | 4 | 0 |
| zikangh | 38 | 18 | 4 | 1 | 0 |
| longvu-db | 37 | 25 | 2 | 3 | 0 |

**Files with `File.exists=false`: 2,143.** `allisonport-db`’s orphaned-file count fell from the reviewer’s 1,303 to 60 after excluding deleted files and bulk commits.

## Bulk commits marked

The cutoff is **more than 100 touched files**. All eight remain in the graph for traces.

| SHA | Files | Subject |
|---|---:|---|
| `1b4a5f97cdb38cc46c241e269f1c8e50d0c9c8cf` | 1,150 | `[Infra] Remove remaining connectors from master (#5620)` |
| `b31589f1c675fcb640d2fa27527ad5da4973e6d8` | 308 | `[INFRA] Upgrade Java version to 11 (#5323)` |
| `6a461b910dcfc7666b239ccdcf13bcad9529d69f` | 190 | `Introduce new docs site (#5013)` |
| `0b65d4621191c40f16274310af219ef65f7cd681` | 189 | `[Other] Redesign docs site (#4621)` |
| `f8cd7725b259c0803bcd13e053e076ea6d99e156` | 189 | `Revert "[Other] Redesign docs site" (#4623)` |
| `db826cf883e24eb8bb643232a29860338a80e98f` | 157 | `[Spark][Infra] Drop support for Spark 3.5 and formally pin to released Spark 4.0.1 (#5616)` |
| `233842fbd93521703a66dd636dc12325fa0f5513` | 106 | `[Spark] Group generatedsuites in folders (#6665)` |
| `a42e8a74f312abb50cccf367578bcd77275ceadb` | 105 | `[Kernel-Spark]Rename io.delta.kernel.spark -> io.delta.spark.internal.v2 and move code to spark/v2 (#5729)` |

## Decision-share results for review

The new query counts distinct `Person -OPENED-> PR -IMPLEMENTS-> Decision` paths at the chosen confidence threshold, then computes the person’s share and lists active co-openers with their PR counts. The evidence query follows those same paths; RFC issue commenters do not count as decision ownership.

- `scottsand-db`: Catalog-Managed Tables, **43/88 (48.9%)**
- `allisonport-db`: IcebergWriterCompatV1, **7/15 (46.7%)**
- `murali-db`: Enforce Vacuum Protocol Check, **1/3 (33.3%)**
- `harperjiang`: IcebergCompatV3, **5/14 (35.7%)**
- `timothyw553`: Enforce Vacuum Protocol Check, **2/3 (66.7%)**
- `johanl-db`: Type Widening, **15/39 (38.5%)**

The integration test verifies `2 of 3` PRs yields a `0.67` share and lists the other opener. The working tree also contains unrelated changes in `pyproject.toml`, `uv.lock`, and `docs/tasks/WP8-api-and-ui.md`; I left those untouched.