// Answers: count people marked Active after the derive pass.
// Parameters: none.
// Shape: count only Person nodes carrying the Active label.
MATCH (p:Person:Active) RETURN count(p) AS active
