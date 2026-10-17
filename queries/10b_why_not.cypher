// Answers: explain which accepted decision replaced a rejected decision, why (when the sources say), and who can explain it.
// Parameters: $slug is the rejected Decision.slug.
// Shape: follow SUPERSEDED_BY and TRACKED_IN, then gather non-bot decision participants as sources to ask.
// rationale is a verbatim excerpt of the replacing decision's tracking issue, stored on SUPERSEDED_BY at load time (null if none).
MATCH (old:Decision {slug:$slug})-[s:SUPERSEDED_BY]->(new:Decision)-[:TRACKED_IN]->(i:Issue)
OPTIONAL MATCH (p:Person)-[part:PARTICIPATED_IN]->(new)
WHERE coalesce(p.bot,false)=false
OPTIONAL MATCH (implementation:PR)-[:IMPLEMENTS]->(new)
OPTIONAL MATCH (implementation)<-[:PART_OF]-(:Commit)-[:TOUCHED]->(f:File)
OPTIONAL MATCH (f)<-[:TOUCHED]-(later:Commit)
WHERE new.decidedOn IS NOT NULL AND later.ts > new.decidedOn
RETURN old.title AS rejected, s.source AS evidence, new.title AS chosenInstead,
       s.rationale AS rationale, s.rationaleSource AS rationaleSource,
       i.number AS discussion, collect(DISTINCT p.login) AS whoToAsk,
       count(DISTINCT later) AS changesSinceDecision
