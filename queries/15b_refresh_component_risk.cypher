// Answers: count each Component's qualifying recent authors so refresh can report coverage changes (no departure simulated).
// Parameters: $since is the activity-window start in epoch milliseconds; the author threshold is 2 commits.
// Shape: KNOWS.commits is all-history, so count distinct in-window non-bulk commits on current files per active non-bot author.
// Refresh has no leaving person, so it reports author counts (0, 1, 2+) rather than the departure risk codes.
MATCH (component:Component)
OPTIONAL MATCH (p:Person:Active)-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component)
WHERE coalesce(p.bot,false)=false AND c.ts > $since
  AND coalesce(c.bulk,false)=false AND coalesce(f.exists,true)=true
WITH component, p, count(DISTINCT c) AS commits
WITH component, collect(CASE WHEN commits >= 2 THEN p.login ELSE null END) AS authors
RETURN component.name AS component, size(authors) AS recentAuthors
ORDER BY component
