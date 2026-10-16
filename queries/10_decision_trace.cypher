// Answers: show recent file-to-decision evidence paths, including how each PR was linked to the decision.
// Parameters: $path is the exact File.path; $limit is the maximum paths.
// Shape: traverse File <- Commit -> PR -> Decision -> Issue, return the path and implementation evidence, ordering stronger links first.
MATCH p=(f:File {path:$path})<-[:TOUCHED]-(c:Commit)-[:PART_OF]->(:PR)-[impl:IMPLEMENTS]->(:Decision)-[:TRACKED_IN]->(:Issue)
RETURN p, impl.confidence AS confidence, impl.via AS via, c.ts AS ts
ORDER BY CASE impl.confidence WHEN 'high' THEN 0 ELSE 1 END, ts DESC
LIMIT $limit
