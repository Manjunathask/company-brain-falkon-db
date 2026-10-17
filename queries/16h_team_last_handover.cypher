// Answers: the most recently saved handover packet for one leaving person and one component.
// Parameters: $key is component:<name>; $person is the leaving login.
// Shape: filter handover observations about that component by person, newest first, one row.
MATCH (a:Agent)-[:WROTE]->(o:Observation {kind: 'handover'})-[:ABOUT]->(:Entity {key: $key})
WHERE o.person = $person
RETURN o.id AS id, o.candidate AS candidate, o.ts AS ts, o.source AS source, a.name AS agent, o.text AS text
ORDER BY o.ts DESC
LIMIT 1
