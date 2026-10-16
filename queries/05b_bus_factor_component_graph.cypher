// Answers: show each reported Component and the top experts counted toward its busFactor.
// Parameters: $areas contains {name, count}; $since, $minCommits, and $minTotal match the table filters.
// Shape: rank each Component's eligible KNOWS edges by commits, keep only the first busFactor experts, and return Component-KNOWS-Person paths.
CALL {
  UNWIND $areas AS area
  MATCH (p:Person)-[k:KNOWS]->(c:Component {name:area.name})
  WHERE k.lastTouched > $since AND k.commits >= $minCommits AND coalesce(p.bot,false)=false
  WITH area,c,p,k ORDER BY k.commits DESC,p.login
  WITH area,c,collect({person:p,knows:k})[0..area.count] AS experts
  UNWIND experts AS expert
  RETURN c AS component,expert.person AS person,expert.knows AS knows
}
MATCH p=(person)-[knows]->(component)
RETURN p LIMIT 200
