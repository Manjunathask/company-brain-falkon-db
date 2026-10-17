// Answers: compare module-level CODEOWNERS declarations with the top three recent, non-bot commit experts.
// Parameters: $since is the activity-window cutoff; $minCommits is minimum in-window commits.
// Shape: KNOWS.commits covers all history, so count distinct in-window commits per person/module before ranking.
// Keep modules with no qualifying authors and collect declarations separately to avoid multiplying counts.
MATCH (m:Module)
OPTIONAL MATCH (o:Person)-[:DECLARED_OWNER]->(m)
WITH m, collect(DISTINCT o.login) AS declared
OPTIONAL MATCH (p:Person)-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_MODULE]->(m)
WHERE c.ts > $since AND coalesce(p.bot,false)=false
  AND coalesce(c.bulk,false)=false AND coalesce(f.exists,true)=true
WITH m, declared, p, count(DISTINCT c) AS commits
ORDER BY commits DESC, p.login
WITH m, declared, collect(CASE WHEN commits >= $minCommits THEN p.login ELSE null END)[0..3] AS actualTop3
RETURN m.name AS module, declared, actualTop3,
       [x IN declared WHERE NOT x IN actualTop3] AS ownersNotInTop3
ORDER BY module
