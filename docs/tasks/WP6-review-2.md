<review>
Reviewer (Claude Code): WP6 round 1 fixes accepted (specific evidence queries, no Cypher in src/, read-only
tools, new what-if metrics; live Active count stable at 294). One change to undo.
</review>

<fixes>
1. The simulator switched from GRAPH.COPY to reading rows from `delta` and re-loading them into a temporary graph
   (09g-09j plus Python batching). GRAPH.COPY was verified on our FalkorDB 4.22 server, is one native command,
   and is the simpler story to explain ("what-if runs on a copy of the graph"). Go back to it:
   GRAPH.COPY delta -> whatif_<login>_<ts>, run 09c membership / 09f collaborators / 09_bridges on the copy,
   09d remove :Active on the copy, 09c again, 09e evidence, GRAPH.DELETE in finally. Delete 09g-09j and their
   QUERIES.md entries. Keep the new metrics and the read-only checks.
   If you switched for a concrete reason (an error, timing, memory), do not revert: reply with the reason and the
   measurement instead.
2. Move `from busfactor.tools import _node, _rel` to a module-level import (if that creates a cycle, move the two
   helpers into a small module both files import, e.g. busfactor/graphjson.py).
</fixes>

<verification_loop>
pytest including integration tests; live `tools simulate_departure --login murali-db` (expect main group 93 -> 90,
cut off chenwang-databricks and dillitz) and its runtime; GRAPH.LIST after.
</verification_loop>

<compact_output_contract>
One line per fix (or the reason you kept the snapshot approach); pytest summary; the live row and runtime.
</compact_output_contract>
