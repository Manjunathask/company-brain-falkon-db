// Answers: list Components with the most derived KNOWS edges for derive sanity reporting.
// Parameters: none.
// Shape: aggregate the Person-to-Component expertise relationships and return the ten largest counts.
MATCH (:Person)-[k:KNOWS]->(c:Component)
RETURN c.name AS component,count(k) AS edges ORDER BY edges DESC,component LIMIT 10
