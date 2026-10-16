<review>
Reviewer (Claude Code) feedback on WP6. The registry, full-text lookup and copy-based what-if work, and
GRAPH.LIST is clean afterwards. Fix the items below; they matter for the demo and for hard rule 5.
</review>

<fixes>
1. Evidence queries must be specific (high). Eight *_graph.cypher files are byte-identical generic
   "all neighbours of these nodes" queries (05, 05b, 07, 08?, 09, 09b, 10b, 11, 12, 13 — check with md5sum).
   On a Module that pulls in thousands of files and the UI would draw noise. Write one specific query per
   tool showing the path behind its answer, each with its own header explaining the shape, LIMIT ~200:
   05/05b   Module|Component <-KNOWS- top experts (the people counted in busFactor)
   06b      gone -AUTHORED-> Commit -TOUCHED-> orphaned File -IN_COMPONENT-> Component
   07       gone -PARTICIPATED_IN-> Decision <-PARTICIPATED_IN- whoToAsk (with confidence on the edges)
   08       gone and successor -AUTHORED-> Commit -TOUCHED-> shared File (only the shared files)
   09       top bridge people and the WORKS_WITH edges among them and to their neighbours
   09b      the largest group's people and WORKS_WITH edges (cap at 200 edges)
   10b      old -SUPERSEDED_BY-> new -TRACKED_IN-> Issue, plus PARTICIPATED_IN into new
   11       Decision <-IMPLEMENTS- PR <-PART_OF- Commit -TOUCHED-> File, and the later commits on those files
   12       Module <-DECLARED_OWNER- declared, Module <-KNOWS- actual top 3
   13       only the matched nodes, no edges
   Delete the generic file. Each tool must use its own evidence query.
2. No Cypher in Python (hard rule 5). whatif.py builds its WCC, REMOVE and evidence queries as Python strings.
   Move them to query files (e.g. 09c_whatif_membership.cypher, 09d_whatif_remove_active.cypher,
   09e_whatif_graph.cypher) with headers. Grep src/ for MATCH/CALL/MERGE strings and move any others too.
3. The what-if metric is wrong for this graph. Live, WCC over :Active + WORKS_WITH gives one group of 93
   people and 289 singletons (people with no WORKS_WITH edge), so "groups before/after" barely moves and a
   split is invisible. Report instead, computed only over people with at least one WORKS_WITH edge:
   mainGroupBefore, mainGroupAfter (size of the largest group), cutOff (people who were in the person's group
   before and are not in the largest group after, listed), directCollaborators (count), betweennessRank, and
   nonSingletonGroups before/after. 09b should also report the largest group and non-singleton group count.
4. Tools must not write. During WP6 the live graph ended with 382 :Active people when the derive rule gives
   294 (reviewer re-ran derive to fix it); GRAPH.COPY was ruled out. Run every tool query through the
   read-only path (falkordb Graph.ro_query -> GRAPH.RO_QUERY) so the server refuses writes; only whatif.py's
   copy may write, and only to its copy. Add an integration test: run every tool on bf_test and assert node,
   edge and per-label counts are unchanged. If you ran anything that wrote to `delta` during WP6, say what.
5. docs/QUERIES.md: replace the generic fallback text with a hand-written 2-3 sentence explanation for every
   file, including the new evidence queries.
</fixes>

<verification_loop>
pytest must pass including integration tests. Live: run `tools simulate_departure --login murali-db` (top
betweenness) and `--login timothyw553`, `tools departure_files --login huan233usc`, `tools orphaned_decisions
--login huan233usc`; include rows and evidence node/edge counts for each. Show `MATCH (p:Active) RETURN
count(p)` before and after the whole run (must be equal) and GRAPH.LIST after.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; the live outputs; anything you disagree with.
</compact_output_contract>
