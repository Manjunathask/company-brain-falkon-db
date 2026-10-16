// Answers: show a rejected Decision's replacement, tracking Issue, and people who participated in the replacement.
// Parameters: $slug is the rejected Decision slug.
// Shape: follow SUPERSEDED_BY and TRACKED_IN, then add confidence-bearing participation paths into the chosen Decision.
MATCH p=(old:Decision {slug:$slug})-[:SUPERSEDED_BY]->(new:Decision)-[:TRACKED_IN]->(:Issue)
RETURN p
UNION
MATCH p=(person:Person)-[:PARTICIPATED_IN]->(new:Decision)<-[:SUPERSEDED_BY]-(:Decision {slug:$slug})
WHERE coalesce(person.bot,false)=false
RETURN p
LIMIT 200
