// Answers: rank active non-bot successors for a departing person's Component by shared recent files, then component commits.
// Parameters: $login is the departing person; $component is the Component.name; $since is the recent activity cutoff.
// Shape: collect distinct current files from focused commits first, then count candidate overlap using only current files and non-bulk commits.
MATCH (gone:Person {login:$login})-[:AUTHORED]->(gc:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(:Component {name:$component})
WHERE gc.ts > $since AND coalesce(gone.bot,false)=false AND coalesce(gc.bulk,false)=false AND coalesce(f.exists,true)=true
WITH gone, collect(DISTINCT f) AS theirs
MATCH (candidate:Person:Active)-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(shared:File)-[:IN_COMPONENT]->(:Component {name:$component})
WHERE candidate <> gone AND coalesce(candidate.bot,false)=false AND c.ts > $since AND shared IN theirs
  AND coalesce(c.bulk,false)=false AND coalesce(shared.exists,true)=true
WITH candidate, theirs, count(DISTINCT shared) AS sharedFiles
OPTIONAL MATCH (candidate)-[k:KNOWS]->(:Component {name:$component})
RETURN candidate.login AS successor, sharedFiles, size(theirs) AS outOf, coalesce(k.commits,0) AS theirCommits
ORDER BY sharedFiles DESC, theirCommits DESC, successor
LIMIT 5
