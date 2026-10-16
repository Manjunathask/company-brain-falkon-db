// Answers: save one user question and answer as an episode linked to touched graph entities.
// Parameters: $sessionId, $text, $ts, $answer, $tools, and $entityKeys.
// Shape: MERGE the session for stable session identity, CREATE a new question per ask, then attach stable Entity keys.
MERGE (s:Session {id: $sessionId})
  ON CREATE SET s.startedAt = $ts
CREATE (q:Question {text: $text, ts: $ts, answer: $answer, tools: $tools})
MERGE (s)-[:ASKED]->(q)
WITH q
UNWIND CASE WHEN size($entityKeys) = 0 THEN [null] ELSE $entityKeys END AS key
FOREACH (_ IN CASE WHEN key IS NULL THEN [] ELSE [1] END |
  MERGE (e:Entity {key: key})
  MERGE (q)-[:ABOUT]->(e))
RETURN q.ts AS ts, size($entityKeys) AS entityCount
