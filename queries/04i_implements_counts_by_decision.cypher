// Answers: count IMPLEMENTS edges for every Decision, including decisions without links.
// Parameters: none.
// Shape: optional-match PR implementation edges so empty decisions remain in the report.
MATCH (d:Decision) OPTIONAL MATCH (:PR)-[r:IMPLEMENTS]->(d)
RETURN d.slug AS slug,count(r) AS count ORDER BY slug
