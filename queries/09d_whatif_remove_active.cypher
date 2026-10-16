// Answers: remove one person's Active label only in the temporary what-if graph.
// Parameters: $login is the person being simulated as departed.
// Shape: match the stable login and remove the label used by the WCC/centrality algorithms.
MATCH (p:Person {login:$login})
REMOVE p:Active
