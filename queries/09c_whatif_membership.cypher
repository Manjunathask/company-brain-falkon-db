// Answers: map each active person with at least one active WORKS_WITH edge to their WCC component.
// Parameters: none; run against the temporary what-if graph before and after removing Active.
// Shape: FalkorDB computes WCC, and the relationship match excludes isolated active people from departure connectivity metrics.
CALL algo.WCC({nodeLabels:['Active'],relationshipTypes:['WORKS_WITH']}) YIELD node,componentId
MATCH (node)-[:WORKS_WITH]-(peer:Person:Active)
WHERE coalesce(node.bot,false)=false AND coalesce(peer.bot,false)=false
RETURN DISTINCT node.login AS person,componentId
