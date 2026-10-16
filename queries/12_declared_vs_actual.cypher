// Answers: compare module-level CODEOWNERS declarations with the top three recent, non-bot commit experts.
// Parameters: $since is the activity-window cutoff; $minCommits is minimum KNOWS commits.
// Shape: collect declared owners, rank recent KNOWS edges by commits, then report missing declared owners.
MATCH (m:Module)
OPTIONAL MATCH (o:Person)-[:DECLARED_OWNER]->(m)
WITH m, collect(DISTINCT o.login) AS declared
OPTIONAL MATCH (p:Person)-[k:KNOWS]->(m)
WHERE k.lastTouched > $since AND k.commits >= $minCommits AND coalesce(p.bot,false)=false
WITH m, declared, p, k
ORDER BY k.commits DESC, p.login
WITH m, declared, collect(p.login)[0..3] AS actualTop3
RETURN m.name AS module, declared, actualTop3,
       [x IN declared WHERE NOT x IN actualTop3] AS ownersNotInTop3
ORDER BY module
