// Answers: count all graph relationships after a derive query.
// Parameters: none.
// Shape: aggregate every relationship type for the derive progress line.
MATCH ()-[r]->() RETURN count(r) AS relationships
