// Answers: retrieve shared observations for selected entities and the newest five overall.
// Parameters: $keys is the set of stable Entity.key values mentioned in the question.
// Shape: entity-specific rows and recent team context are deduplicated by observation ID.
MATCH (a:Agent)-[:WROTE]->(o:Observation)-[:ABOUT]->(e:Entity)
WITH a, o, e, size($keys) > 0 AND e.key IN $keys AS related
WITH a, o, e, related ORDER BY o.ts DESC
WITH collect(CASE WHEN related THEN {id:o.id, agent:a.name, text:o.text, ts:o.ts, kind:o.kind, source:o.source, entity:e.key} END) AS relatedRows,
     collect({id:o.id, agent:a.name, text:o.text, ts:o.ts, kind:o.kind, source:o.source, entity:e.key})[0..5] AS recentRows
UNWIND relatedRows + recentRows AS row
WITH row WHERE row IS NOT NULL
RETURN DISTINCT row.id AS id, row.agent AS agent, row.text AS text, row.ts AS ts,
       row.kind AS kind, row.source AS source, row.entity AS entity
ORDER BY ts DESC
