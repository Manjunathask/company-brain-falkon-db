// Answers: list the five strongest WORKS_WITH pairs.
// Parameters: none.
// Shape: order collaboration edges by shared-file count and stable logins.
MATCH (a:Person)-[w:WORKS_WITH]->(b:Person)
RETURN a.login AS personA,b.login AS personB,w.sharedFiles AS sharedFiles
ORDER BY sharedFiles DESC,personA,personB LIMIT 5
