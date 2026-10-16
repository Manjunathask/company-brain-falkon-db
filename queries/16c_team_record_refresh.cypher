// Answers: create an idempotent shared RefreshRun and connect its observations.
// Parameters: $id, $ts, $newCommits, $newPRs, and $observationIds.
// Shape: merge the run by deterministic ID and match observations by their stable IDs.
MERGE (r:RefreshRun {id: $id})
SET r.ts = $ts, r.newCommits = $newCommits, r.newPRs = $newPRs
WITH r
UNWIND $observationIds AS observationId
MATCH (o:Observation {id: observationId})
MERGE (r)-[:OBSERVED]->(o)
RETURN r.id AS id, r.ts AS ts, r.newCommits AS newCommits, r.newPRs AS newPRs, count(o) AS observations
