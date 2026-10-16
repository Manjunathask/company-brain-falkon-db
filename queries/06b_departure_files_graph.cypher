// Answers: show the exact orphaned files reported for a departing person, with their source commits and Components.
// Parameters: $login is the person; $since is the activity cutoff; $componentPrefix optionally narrows component names; $includeTestResources includes fixture-only components when true.
// Shape: reproduce the orphan test with current files and non-bulk commits, including the same scope filters, then return evidence paths.
MATCH p=(gone:Person {login:$login})-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component:Component)
WHERE c.ts > $since AND coalesce(gone.bot,false)=false AND coalesce(c.bulk,false)=false AND coalesce(f.exists,true)=true
  AND ($componentPrefix = '' OR component.name STARTS WITH $componentPrefix)
  AND ($includeTestResources OR NOT component.name ENDS WITH '/(test-resources)')
OPTIONAL MATCH (other:Person:Active)-[:AUTHORED]->(otherCommit:Commit)-[:TOUCHED]->(f)
WHERE other <> gone AND otherCommit.ts > $since AND coalesce(other.bot,false)=false AND coalesce(otherCommit.bulk,false)=false
WITH p,f,collect(DISTINCT other.login) AS editors
WHERE size(editors)=0
RETURN p LIMIT 200
