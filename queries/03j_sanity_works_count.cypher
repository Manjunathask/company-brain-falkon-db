// Answers: count derived WORKS_WITH relationships.
// Parameters: none.
// Shape: count the collaboration relationships in the graph.
MATCH ()-[w:WORKS_WITH]->() RETURN count(w) AS relationships
