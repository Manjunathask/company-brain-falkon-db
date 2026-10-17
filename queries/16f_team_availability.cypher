// Answers: the latest availability note for every person who has one, so handover candidates can be skipped with their reason.
// Parameters: none.
// Shape: order each person's availability observations newest first and keep the first; the caller treats status 'unavailable' as an exclusion.
MATCH (a:Agent)-[:WROTE]->(o:Observation {kind: 'availability'})-[:ABOUT]->(e:Entity)
WITH e, a, o
ORDER BY o.ts DESC
WITH e, collect({status: o.status, reason: o.reason, ts: o.ts, source: o.source, agent: a.name})[0] AS latest
RETURN e.key AS entity, latest.status AS status, latest.reason AS reason, latest.ts AS ts,
       latest.source AS source, latest.agent AS agent
