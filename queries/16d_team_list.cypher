// Answers: list recent shared Observations and RefreshRuns for the team-memory API.
// Parameters: $limit caps each list.
// Shape: collect observations and refresh records independently to avoid cross-product duplication.
OPTIONAL MATCH (a:Agent)-[:WROTE]->(o:Observation)-[:ABOUT]->(e:Entity)
WITH collect({id:o.id, agent:a.name, text:o.text, ts:o.ts, kind:o.kind, source:o.source, entity:e.key}) AS observations
OPTIONAL MATCH (r:RefreshRun)
WITH observations, collect({id:r.id, ts:r.ts, newCommits:r.newCommits, newPRs:r.newPRs}) AS refreshRuns
RETURN [x IN observations WHERE x.ts IS NOT NULL][0..$limit] AS observations,
       [x IN refreshRuns WHERE x.ts IS NOT NULL][0..$limit] AS refreshRuns
