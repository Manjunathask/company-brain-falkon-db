// Answers: delete shared team-memory observations written by one anonymous visitor and return the number removed.
// Parameters: $agent is exactly chat:<visitor-id>; callers validate the visitor-id before running this query.
// Shape: collect only observations written by that agent, detach-delete those observations and its Agent node, and return zero when none exist.
OPTIONAL MATCH (a:Agent {name:$agent})-[:WROTE]->(o:Observation)
WITH a, collect(DISTINCT o) AS observations, count(DISTINCT o) AS removed
FOREACH (observation IN observations | DETACH DELETE observation)
FOREACH (_ IN CASE WHEN a IS NULL THEN [] ELSE [1] END | DETACH DELETE a)
RETURN removed AS removed
