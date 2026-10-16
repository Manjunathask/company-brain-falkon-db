// Answers: rank Components by recent authored file touches for the path-mapping report.
// Parameters: $since is an epoch-millisecond activity cutoff.
// Shape: traverse authored commits through touched files into Components and count matching touches.
MATCH (:Person)-[:AUTHORED]->(commit:Commit)-[:TOUCHED]->(:File)-[:IN_COMPONENT]->(c:Component)
WHERE commit.ts > $since
RETURN c.name AS component,count(*) AS touches ORDER BY touches DESC,component LIMIT 40
