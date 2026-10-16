// Answers: find decisions for which the departing person is the only currently active participant at the requested evidence confidence.
// Parameters: $login is the person; $minConfidence is 'high' or 'low'.
// Shape: filter PARTICIPATED_IN by confidence before collecting active participants, then report the other participants and people to ask.
MATCH (gone:Person {login:$login})-[gp:PARTICIPATED_IN]->(d:Decision)
WITH gone, gp, d
WHERE coalesce(gone.bot,false)=false AND gp.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
OPTIONAL MATCH (other:Person:Active)-[op:PARTICIPATED_IN]->(d)
WHERE other <> gone AND coalesce(other.bot,false)=false
  AND op.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
WITH gone, d, collect(DISTINCT other.login) AS others
WHERE size(others)=0
OPTIONAL MATCH (ask:Person)-[ap:PARTICIPATED_IN]->(d)
WHERE ask <> gone AND coalesce(ask.bot,false)=false
  AND ap.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
RETURN d.title AS decision, d.status AS status, others AS othersStillActive,
       collect(DISTINCT ask.login) AS whoToAsk
ORDER BY decision
