// Answers: explain which accepted decision replaced a rejected decision and who can explain the replacement.
// Parameters: $slug is the rejected Decision.slug.
// Shape: follow SUPERSEDED_BY and TRACKED_IN, then gather non-bot decision participants as sources to ask.
MATCH (old:Decision {slug:$slug})-[s:SUPERSEDED_BY]->(new:Decision)-[:TRACKED_IN]->(i:Issue)
OPTIONAL MATCH (p:Person)-[part:PARTICIPATED_IN]->(new)
WHERE coalesce(p.bot,false)=false
RETURN old.title AS rejected, s.source AS evidence, new.title AS chosenInstead,
       i.number AS discussion, collect(DISTINCT p.login) AS whoToAsk
