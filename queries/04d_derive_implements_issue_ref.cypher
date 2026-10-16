// Answers: link PRs to decisions whose tracked RFC issue the PR body references.
// Parameters: none.
// Shape: this is the strongest evidence because it follows explicit graph links; keep source history and do not overwrite an existing high-confidence via.
MATCH (pr:PR)-[:REFERENCES]->(:Issue)<-[:TRACKED_IN]-(d:Decision)
MERGE (pr)-[r:IMPLEMENTS]->(d)
SET r.sources = CASE WHEN 'issue-ref' IN coalesce(r.sources, []) THEN coalesce(r.sources, []) ELSE coalesce(r.sources, []) + 'issue-ref' END,
    r.via = CASE WHEN r.confidence = 'high' AND r.via IS NOT NULL THEN r.via ELSE 'issue-ref' END,
    r.confidence = 'high'
