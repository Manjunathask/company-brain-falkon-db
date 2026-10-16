// Answers: show both the departing person and each ranked successor on only their shared recent files.
// Parameters: $login, $successors, $component, and $since identify the overlap result.
// Shape: traverse from the departing person's authored commit through a Component file to a candidate's touching commit and author.
MATCH p=(gone:Person {login:$login})-[:AUTHORED]->(gc:Commit)-[:TOUCHED]->(file:File)<-[:TOUCHED]-(cc:Commit)<-[:AUTHORED]-(candidate:Person:Active)
MATCH (file)-[:IN_COMPONENT]->(:Component {name:$component})
WHERE gc.ts > $since AND cc.ts > $since AND candidate.login IN $successors
  AND coalesce(gone.bot,false)=false AND coalesce(candidate.bot,false)=false
RETURN p LIMIT 200
