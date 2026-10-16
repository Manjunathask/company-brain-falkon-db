// Answers: show the departing person's participation in each orphaned Decision and every qualifying person to ask.
// Parameters: $login, $decisions, and $minConfidence select the result evidence.
// Shape: traverse confidence-qualified PARTICIPATED_IN edges in both directions around each selected Decision.
MATCH p=(gone:Person {login:$login})-[g:PARTICIPATED_IN]->(d:Decision)
WHERE d.title IN $decisions AND g.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
RETURN p
UNION
MATCH p=(who:Person)-[r:PARTICIPATED_IN]->(d:Decision)
WHERE d.title IN $decisions AND who.login <> $login AND coalesce(who.bot,false)=false
  AND r.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
RETURN p
LIMIT 200
