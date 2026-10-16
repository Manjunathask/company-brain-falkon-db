// Answers: show the exact orphaned files reported for a departing person, with their source commits and Components.
// Parameters: $login is the person; $since is the activity cutoff.
// Shape: reproduce the orphan test by excluding files with another active non-bot editor, then return person-to-Component evidence paths.
MATCH p=(gone:Person {login:$login})-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component:Component)
WHERE c.ts > $since AND coalesce(gone.bot,false)=false
OPTIONAL MATCH (other:Person:Active)-[:AUTHORED]->(otherCommit:Commit)-[:TOUCHED]->(f)
WHERE other <> gone AND otherCommit.ts > $since AND coalesce(other.bot,false)=false
WITH p,f,collect(DISTINCT other.login) AS editors
WHERE size(editors)=0
RETURN p LIMIT 200
