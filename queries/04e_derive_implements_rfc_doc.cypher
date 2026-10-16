// Answers: link PRs that changed an RFC markdown document to that RFC's decision.
// Parameters: none.
// Shape: match the RFC slug at the end of protocol_rfcs paths, including accepted/rejected moves; exclude README/template by exact filename shape.
MATCH (d:Decision)
MATCH (f:File)<-[:TOUCHED]-(c:Commit)-[:PART_OF]->(pr:PR)
WHERE f.path STARTS WITH 'protocol_rfcs/'
  AND f.path ENDS WITH ('/' + d.slug + '.md')
MERGE (pr)-[r:IMPLEMENTS]->(d)
SET r.sources = CASE WHEN 'rfc-doc' IN coalesce(r.sources, []) THEN coalesce(r.sources, []) ELSE coalesce(r.sources, []) + 'rfc-doc' END,
    r.via = CASE WHEN r.confidence = 'high' AND r.via IS NOT NULL THEN r.via ELSE 'rfc-doc' END,
    r.confidence = 'high'
