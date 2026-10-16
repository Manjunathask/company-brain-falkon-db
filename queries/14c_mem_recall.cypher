// Answers: recall recent questions and corrections for given entities, or the user's last five episodes.
// Parameters: $keys is a list of Entity.key strings; $limit caps fallback episode history.
// Shape: optional matches select explicit entities or recent questions without CALL subquery imports.
OPTIONAL MATCH (e:Entity)
WHERE size($keys) > 0 AND e.key IN $keys
OPTIONAL MATCH (s:Session)-[:ASKED]->(q:Question)
WHERE size($keys) = 0
WITH e, q ORDER BY q.ts DESC
WITH e, collect(q)[0..$limit] AS recentQuestions
UNWIND CASE WHEN e IS NULL THEN recentQuestions ELSE [null] END AS recent
OPTIONAL MATCH (e)<-[:ABOUT]-(known:Question)
OPTIONAL MATCH (recent)-[:ABOUT]->(fromRecent:Entity)
WITH coalesce(e, fromRecent) AS entity, known, recent
OPTIONAL MATCH (entity)<-[:CORRECTS]-(c:Correction)
RETURN entity.key AS entity,
       max(coalesce(known.ts, recent.ts)) AS lastAsked,
       collect(DISTINCT coalesce(known.text, recent.text))[0..3] AS earlierQuestions,
       collect(DISTINCT {text:c.text, source:c.source, ts:c.ts}) AS corrections
ORDER BY lastAsked DESC
