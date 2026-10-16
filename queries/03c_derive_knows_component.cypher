// Answers: derive each non-bot person's expertise and latest touch per Component.
// Parameters: none.
// Shape: delete all old Component KNOWS edges first, then count distinct current-file, non-bulk commits so mass edits and deleted files do not inflate expertise.
OPTIONAL MATCH ()-[old:KNOWS]->(:Component)
DELETE old
WITH count(old) AS cleared
MATCH (p:Person)-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component:Component)
WHERE coalesce(p.bot, false) = false AND coalesce(c.bulk, false) = false AND coalesce(f.exists, true) = true
WITH p, component, count(DISTINCT c) AS commits, max(c.ts) AS lastTouched
MERGE (p)-[k:KNOWS]->(component)
SET k.commits = commits, k.lastTouched = lastTouched
