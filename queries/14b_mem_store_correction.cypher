// Answers: store a user correction as memory attached to a stable graph entity key.
// Parameters: $key, $text, $ts, and $source.
// Shape: MERGE the entity but CREATE each correction so its source and timestamp remain auditable.
MERGE (e:Entity {key: $key})
CREATE (c:Correction {text: $text, ts: $ts, source: $source})
MERGE (c)-[:CORRECTS]->(e)
RETURN e.key AS entity, c.text AS correction, c.ts AS ts
