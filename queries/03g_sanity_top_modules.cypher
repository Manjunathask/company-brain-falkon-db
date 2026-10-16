// Answers: list Modules with the most derived KNOWS edges for derive sanity reporting.
// Parameters: none.
// Shape: aggregate the Person-to-Module expertise relationships and return the ten largest counts.
MATCH (:Person)-[k:KNOWS]->(m:Module)
RETURN m.name AS module,count(k) AS edges ORDER BY edges DESC,module LIMIT 10
