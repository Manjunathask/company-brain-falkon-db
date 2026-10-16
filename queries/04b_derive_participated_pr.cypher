// Answers: mark non-bot people who opened or reviewed a PR that implements a decision.
// Parameters: none.
// Shape: include low-confidence title links because authorship/review is still participation evidence; copy confidence so downstream queries can filter it. 04c upgrades issue participants to high confidence.
OPTIONAL MATCH ()-[old:PARTICIPATED_IN]->()
DELETE old
WITH count(old) AS cleared
MATCH (p:Person)-[:OPENED|REVIEWED]->(:PR)-[impl:IMPLEMENTS]->(d:Decision)
WHERE coalesce(p.bot, false) = false
MERGE (p)-[part:PARTICIPATED_IN]->(d)
SET part.confidence = CASE WHEN part.confidence = 'high' THEN 'high' ELSE impl.confidence END,
    part.via = 'pr'
