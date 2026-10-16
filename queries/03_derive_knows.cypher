// Answers: derive each non-bot person's commit expertise and most recent touch per module.
// Parameters: none.
// Shape: clear old derived edges for exact reruns, then count distinct commits because one commit can touch multiple files in a module.
OPTIONAL MATCH ()-[old:KNOWS]->()
DELETE old
WITH count(old) AS cleared
MATCH (p:Person)-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(:File)-[:IN_MODULE]->(m:Module)
WHERE coalesce(p.bot, false) = false
WITH p, m, count(DISTINCT c) AS commits, max(c.ts) AS lastTouched
MERGE (p)-[k:KNOWS]->(m)
SET k.commits = commits, k.lastTouched = lastTouched
