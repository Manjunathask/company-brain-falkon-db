// Answers: show each reported Module and the top experts counted toward its busFactor.
// Parameters: $areas contains {name, count}; $since, $minCommits, and $minTotal match the table filters.
// Shape: rank each Module's eligible KNOWS edges by commits, keep only the first busFactor experts, and return Module-KNOWS-Person paths.
CALL {
  UNWIND $areas AS area
  MATCH (p:Person)-[k:KNOWS]->(m:Module {name:area.name})
  WHERE k.lastTouched > $since AND k.commits >= $minCommits AND coalesce(p.bot,false)=false
  WITH area,m,p,k ORDER BY k.commits DESC,p.login
  WITH area,m,collect({person:p,knows:k})[0..area.count] AS experts
  UNWIND experts AS expert
  RETURN m AS module,expert.person AS person,expert.knows AS knows
}
MATCH p=(person)-[knows]->(module)
RETURN p LIMIT 200
