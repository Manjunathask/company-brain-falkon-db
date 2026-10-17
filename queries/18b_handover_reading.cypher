// Answers: which of the leaving person's recent PRs in one code area a successor should read first.
// Parameters: $login is the leaving person; $component is the Component.name; $since is the activity-window start (epoch ms); $limit caps the list.
// Shape: start from the person's in-window, non-bulk commits on current files in the area, group them by PR, then add decision links and reviewers in separate stages.
// Order: PRs with an explicit (high-confidence) decision link first, then the most files touched here, then the most recently merged.
MATCH (gone:Person {login:$login})-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(:Component {name:$component})
WHERE c.ts > $since AND coalesce(c.bulk,false)=false AND coalesce(f.exists,true)=true
MATCH (c)-[:PART_OF]->(pr:PR)
WITH pr, count(DISTINCT f) AS filesHere
OPTIONAL MATCH (pr)-[link:IMPLEMENTS]->(d:Decision)
WITH pr, filesHere,
     collect(CASE WHEN d IS NULL THEN null ELSE {title: d.title, confidence: link.confidence} END) AS decisions,
     max(CASE WHEN link.confidence = 'high' THEN 1 ELSE 0 END) AS hasExplicit
OPTIONAL MATCH (reviewer:Person)-[:REVIEWED]->(pr)
WHERE coalesce(reviewer.bot,false)=false
WITH pr, filesHere, decisions, hasExplicit, collect(DISTINCT reviewer.login) AS reviewers
ORDER BY hasExplicit DESC, filesHere DESC, pr.mergedAt DESC, pr.number DESC
LIMIT $limit
RETURN pr.number AS number, pr.title AS title, pr.mergedAt AS mergedAt, filesHere, decisions, reviewers
