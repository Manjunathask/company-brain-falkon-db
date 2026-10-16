// Answers: report total node and relationship counts for a graph.
// Parameters: none.
// Shape: aggregate nodes and relationships in isolated subqueries and return a single count row.
CALL { MATCH (n) RETURN count(n) AS nodes }
CALL { MATCH ()-[r]->() RETURN count(r) AS relationships }
RETURN nodes,relationships
