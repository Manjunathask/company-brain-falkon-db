// Answers: count Component nodes after path mapping.
// Parameters: none.
// Shape: count all Component nodes.
MATCH (c:Component) RETURN count(c) AS components
