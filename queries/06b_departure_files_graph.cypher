// Answers: show the exact orphaned files reported for a departing person, with their source commits and Components.
// Parameters: $login is the person; $since is the activity cutoff.
// Shape: reproduce the orphan test with current files and non-bulk commits, then return person-to-Component paths; deleted history remains available to decision tracing.
MATCH p=(gone:Person {login:$login})-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component:Component)
WHERE c.ts > $since AND coalesce(gone.bot,false)=false AND coalesce(c.bulk,false)=false AND coalesce(f.exists,true)=true
OPTIONAL MATCH (other:Person:Active)-[:AUTHORED]->(otherCommit:Commit)-[:TOUCHED]->(f)
WHERE other <> gone AND otherCommit.ts > $since AND coalesce(other.bot,false)=false AND coalesce(otherCommit.bulk,false)=false
WITH p,f,collect(DISTINCT other.login) AS editors
WHERE size(editors)=0
RETURN p LIMIT 200
