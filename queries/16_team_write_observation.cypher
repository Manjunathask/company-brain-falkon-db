// Answers: write one shared observation about a stable entity key in mem_team.
// Parameters: $id, $agent, $text, $ts, $kind, $source, and $key.
// Shape: stable Observation.id makes watcher retries idempotent; Entity.key joins to delta in Python.
MERGE (a:Agent {name: $agent})
MERGE (e:Entity {key: $key})
MERGE (o:Observation {id: $id})
SET o.text = $text, o.ts = $ts, o.kind = $kind, o.source = $source
MERGE (a)-[:WROTE]->(o)
MERGE (o)-[:ABOUT]->(e)
RETURN o.id AS id, o.text AS text, o.ts AS ts, o.kind AS kind, o.source AS source, a.name AS agent, e.key AS entity
