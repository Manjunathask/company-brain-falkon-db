// Answers: derive each non-bot person's expertise and latest touch per Component.
// Parameters: none.
// Shape: delete all old Component KNOWS edges first, then count distinct commits so multi-file commits count once and reruns exactly reflect source edges.
OPTIONAL MATCH ()-[old:KNOWS]->(:Component)
DELETE old
WITH count(old) AS cleared
MATCH (p:Person)-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(:File)-[:IN_COMPONENT]->(component:Component)
WHERE coalesce(p.bot, false) = false
WITH p, component, count(DISTINCT c) AS commits, max(c.ts) AS lastTouched
MERGE (p)-[k:KNOWS]->(component)
SET k.commits = commits, k.lastTouched = lastTouched
