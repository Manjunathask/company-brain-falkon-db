## WP5 complete

**Module remains unchanged** as the first path segment. Each loaded file now links to a `Component`, and each component links to its existing module. I extended `01_load_commits.cypher` because it already loads each file row; I also added component links for RFC document files in `02_load_decisions.cypher`.

The derived query rebuilds component `KNOWS` edges exactly, counts distinct commits, and excludes bots. The bus-factor queries report people and total commits; the departure queries report component risk and orphaned files. The README now defines Components, and the progress log has a WP5 entry.

## Verification

- `.venv/Scripts/python -m pytest -q`: **31 passed**
- Rebuilt the live graph with `load all → link_decisions → derive`. The load processed 2,234 commits in 5 batches; derive created 551 module and 1,915 component `KNOWS` edges.
- `python -m busfactor.ingest.components`: **302 total components, 194 source components**.

Top 15 components by recent file touches:

| Component | Touches | Component | Touches |
|---|---:|---|---:|
| spark/(core) | 1,947 | spark/generatedsuites | 257 |
| spark/v2/spark | 867 | docs/source | 250 |
| connectors/docs | 841 | root | 211 |
| kernel/kernel-api/(core) | 554 | kernel-spark/spark | 206 |
| kernel/kernel-defaults/(core) | 484 | kernel/kernel-api/util | 185 |
| spark/amt | 457 | .github/workflows | 167 |
| spark/commands | 372 | docs/src | 167 |
| spark/src | 351 | spark/coordinatedcommits | 163 |
| spark/sources | 318 |  |  |

The component command reported **544 source paths without a matching explicit package-prefix rule** and printed their fallback placements. For example, `connectors/examples/flink-example/src/main/java/org/example/sink/DeltaSinkExample.java` maps to `connectors/examples/flink-example/org`. These paths were assigned rather than dropped.

I ran `scripts/try_queries.py` for both requested logins. The extracted output confirms component-level risk and orphaned files:

| Login | Module `spark` bus factor | Component risk: orphaned / at risk / covered | Orphaned files |
|---|---|---:|---:|
| huan233usc | 16; top expert `ctring`; 81 people, 1,170 commits | 12 / 5 / 34 | 65 across 22 components |
| scottsand-db | 16; top expert `ctring`; 81 people, 1,170 commits | 5 / 8 / 16 | 52 across 10 components |

For `huan233usc`, the largest orphan groups were `kernel-spark/spark` (20 files), `spark/v2/spark` (12), and `spark/(core)` (5). For `scottsand-db`, they were `unity/unity` (15), `kernel/unitycatalog/unitycatalog` (9), and `kernel/kernel-defaults/(core)` (8). The headline check passes without threshold tuning.

## Changed files

- **Loader and derive:** [components.py](/C:/Users/skman/Documents/Hackathon/src/busfactor/ingest/components.py), [load.py](/C:/Users/skman/Documents/Hackathon/src/busfactor/load.py), [derive.py](/C:/Users/skman/Documents/Hackathon/src/busfactor/derive.py)
- **Queries:** `00_indexes`, `01_load_commits`, `02_load_decisions`, `03c_derive_knows_component`, `05_bus_factor`, `05b_bus_factor_component`, `06_departure_impact`, `06b_departure_files`
- **Reviewer runner:** [try_queries.py](/C:/Users/skman/Documents/Hackathon/scripts/try_queries.py)
- **Tests and docs:** [test_components.py](/C:/Users/skman/Documents/Hackathon/tests/test_components.py), [test_graph_integration.py](/C:/Users/skman/Documents/Hackathon/tests/test_graph_integration.py), `tests/test_derive_queries.py`, [README.md](/C:/Users/skman/Documents/Hackathon/README.md), [PROGRESS.md](/C:/Users/skman/Documents/Hackathon/docs/PROGRESS.md)

No commit was made.