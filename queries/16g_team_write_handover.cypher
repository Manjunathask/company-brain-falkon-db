// Answers: save a drafted handover packet to shared team memory so other visitors and later sessions see it.
// Parameters: $id, $agent, $key (component:<name>), $person (leaving login), $candidate (suggested successor login), $text, $ts, $source.
// Shape: one Observation of kind 'handover' about the component; the newest one per person and component is the current plan.
MERGE (a:Agent {name: $agent})
MERGE (e:Entity {key: $key})
MERGE (o:Observation {id: $id})
SET o.text = $text, o.ts = $ts, o.kind = 'handover', o.source = $source, o.person = $person, o.candidate = $candidate
MERGE (a)-[:WROTE]->(o)
MERGE (o)-[:ABOUT]->(e)
RETURN o.id AS id, e.key AS entity, o.person AS person, o.candidate AS candidate, o.ts AS ts, o.source AS source, a.name AS agent
