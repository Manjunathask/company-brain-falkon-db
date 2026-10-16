// Answers: count participating people for each decision.
// Parameters: none.
// Shape: optional-match participants so decisions with no participation remain visible.
MATCH (d:Decision) OPTIONAL MATCH (:Person)-[r:PARTICIPATED_IN]->(d)
RETURN d.title AS decision,count(r) AS people ORDER BY decision
