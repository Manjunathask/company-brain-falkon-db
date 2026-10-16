// Answers: rank active non-bot people by betweenness in the recent WORKS_WITH network.
// Parameters: $limit is the maximum number of people returned.
// Shape: FalkorDB computes betweenness on the Active/WORKS_WITH projection; the query returns the highest scores.
CALL algo.betweenness({nodeLabels:['Active'], relationshipTypes:['WORKS_WITH']}) YIELD node, score
WHERE coalesce(node.bot,false)=false
RETURN node.login AS person, score
ORDER BY score DESC, person
LIMIT $limit
