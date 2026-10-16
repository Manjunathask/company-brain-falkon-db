// Answers: mark non-bot people who opened or commented on an RFC issue tracked by a decision.
// Parameters: none.
// Shape: MERGE on the person/decision pair makes this path replay-safe; preserve `pr` when both evidence paths exist.
MATCH (p:Person)-[:OPENED|COMMENTED]->(:Issue)<-[:TRACKED_IN]-(d:Decision)
WHERE coalesce(p.bot, false) = false
MERGE (p)-[part:PARTICIPATED_IN]->(d)
SET part.via = coalesce(part.via, 'issue')
