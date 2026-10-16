<review>
Reviewer (Claude Code) feedback on WP5. The headline check passes (huan233usc: 65 orphaned files across 22
components). The component rule needs one cleanup round so names are meaningful in the demo. Evidence is
from the live graph and `component_of` on real paths.
</review>

<fixes>
1. Missing package prefixes produce vague names. Add to the explicit list (longest match wins):
   io/delta/spark/internal/v2   (spark/v2/src/main/java/io/delta/spark/internal/v2/adapters/... is now
                                 `spark/v2/spark`; should be `spark/v2/adapters`, `spark/v2/catalog`, ...)
   io/delta/kernel/spark        (kernel-spark/.../io/delta/kernel/spark/catalog/... -> `kernel-spark/catalog`)
   io/delta/sharing/spark, io/delta/standalone/internal, io/delta/standalone, org/apache/iceberg,
   com/databricks/spark.
   Then a generic, documented fallback: if the first remaining segment is org, com, io or net, drop that
   reverse-DNS prefix (3 segments) before taking the component directory. No more `iceberg/org`, `spark/com`.
2. Source roots: also accept versioned folders like `src/main/scala-2.12/` (connectors/standalone uses them).
3. Test resources are fixtures, not knowledge areas: `src/test/resources/...` -> `<project>/(test-resources)`
   (today 40 parquet/crc files form `spark/delta`).
4. Non-source fallback must not turn a file into a component. Use the second segment only when it is a
   directory (the path has 3+ segments); otherwise `<first segment>/(files)`. Today `.github/CODEOWNERS`,
   `docs/.nvmrc`, `flink/README.md`, `project/SparkMimaExcludes.scala` and every
   `protocol_rfcs/<rfc>.md` are their own components. Root-level files stay `root`.
5. 05_bus_factor and 05b_bus_factor_component: add `$minTotal` (minimum recent commits in the module or
   component to be reported) so 2-commit components do not crowd the top of the list. try_queries.py
   defaults it to 5 and prints how many were filtered out.
6. Print the remaining unplaced/fallback count from `python -m busfactor.ingest.components`, grouped by the
   rule that placed them, so the reviewer can see the fallback is rare.
</fixes>

<verification_loop>
pytest must pass including integration tests (FalkorDB is reachable). Update test_components.py for each
rule above with the real example paths quoted here. Rebuild the live graph (load all -> link_decisions ->
derive) and rerun `scripts/try_queries.py --login huan233usc`; include the component bus-factor top 15 and
the 06b orphaned-files table.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; component summary (count, fallback counts by rule); the two tables.
</compact_output_contract>
