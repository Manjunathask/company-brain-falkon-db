// Answers: how many Components have names starting with the requested prefix.
// Parameters: $prefix is a non-empty Component name prefix.
// Shape: count distinct matching nodes so zero is explicit and no paths multiply the count.
MATCH (c:Component) WHERE c.name STARTS WITH $prefix
RETURN count(DISTINCT c) AS count
