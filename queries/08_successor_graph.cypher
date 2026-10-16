// Answers: show both the departing person and each ranked successor on only their shared recent files.
// Parameters: $login, $successors, $component, and $since identify the overlap result.
// Shape: traverse only current files touched by non-bulk commits, so evidence paths match the overlap used to rank successors.
MATCH p=(gone:Person {login:$login})-[:AUTHORED]->(gc:Commit)-[:TOUCHED]->(file:File)<-[:TOUCHED]-(cc:Commit)<-[:AUTHORED]-(candidate:Person:Active)
MATCH (file)-[:IN_COMPONENT]->(:Component {name:$component})
WHERE gc.ts > $since AND cc.ts > $since AND candidate.login IN $successors
  AND coalesce(gc.bulk,false)=false AND coalesce(cc.bulk,false)=false AND coalesce(file.exists,true)=true
  AND coalesce(gone.bot,false)=false AND coalesce(candidate.bot,false)=false
RETURN p LIMIT 200
