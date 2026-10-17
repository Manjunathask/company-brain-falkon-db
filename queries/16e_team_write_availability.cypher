// Answers: record in shared team memory that a person is or is not available to take over work.
// Parameters: $id, $agent (chat:<visitor> or another writer), $key (person:<login>), $status ('unavailable' or 'available'), $reason, $text, $ts, $source.
// Shape: one Observation per note with kind 'availability'; notes are never edited, the newest one per person wins; Entity.key joins to delta in Python.
MERGE (a:Agent {name: $agent})
MERGE (e:Entity {key: $key})
MERGE (o:Observation {id: $id})
SET o.text = $text, o.ts = $ts, o.kind = 'availability', o.source = $source, o.status = $status, o.reason = $reason
MERGE (a)-[:WROTE]->(o)
MERGE (o)-[:ABOUT]->(e)
RETURN o.id AS id, e.key AS entity, o.status AS status, o.reason AS reason, o.ts AS ts, o.source AS source, a.name AS agent
