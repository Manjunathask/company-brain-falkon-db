// Answers: mark non-bot people who opened or reviewed a PR that implements a decision.
// Parameters: none.
// Shape: clear all old derived participation first (04c runs immediately after); MERGE on the person/decision pair makes this path replay-safe, and `via` records the evidence path.
OPTIONAL MATCH ()-[old:PARTICIPATED_IN]->()
DELETE old
WITH count(old) AS cleared
MATCH (p:Person)-[:OPENED|REVIEWED]->(:PR)-[:IMPLEMENTS]->(d:Decision)
WHERE coalesce(p.bot, false) = false
MERGE (p)-[part:PARTICIPATED_IN]->(d)
SET part.via = 'pr'
