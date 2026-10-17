// Answers: show only the leaving/remaining authors and listed reviewers from the departure table.
// Parameters: $login, $areas ({name, remaining, reviewers}), $since (epoch ms).
// Shape: reuse table membership for KNOWS; separately select up to 3 qualifying area PRs per listed reviewer.
CALL {
  UNWIND $areas AS area
  UNWIND [$login] + area.remaining AS login
  MATCH p=(person:Person {login:login})-[:KNOWS]->(:Component {name:area.name})
  RETURN p
  UNION
  UNWIND $areas AS area
  MATCH (component:Component {name:area.name})
  WITH area, component
  MATCH (component)<-[:IN_COMPONENT]-(f:File)<-[:TOUCHED]-(c:Commit)-[:PART_OF]->(pr:PR)
  WHERE c.ts > $since AND coalesce(c.bulk,false)=false AND coalesce(f.exists,true)=true
  WITH DISTINCT area, pr
  MATCH (reviewer:Person:Active)-[review:REVIEWED]->(pr)
  WHERE reviewer.login IN area.reviewers AND reviewer.login <> $login
    AND coalesce(reviewer.bot,false)=false AND review.at > $since
  WITH DISTINCT area, reviewer, pr
  ORDER BY pr.number DESC
  WITH area, reviewer, collect(pr)[0..3] AS prs
  UNWIND prs AS pr
  MATCH p=(reviewer)-[:REVIEWED]->(pr)
  RETURN p
}
RETURN p
