// Answers: return the newest loaded Commit timestamp and PR update timestamp.
// Parameters: none.
// Shape: independent optional matches preserve a watermark row for empty graphs.
OPTIONAL MATCH (c:Commit)
WITH max(c.ts) AS newestCommit
OPTIONAL MATCH (pr:PR)
RETURN newestCommit, max(coalesce(pr.updatedAt, pr.mergedAt, pr.createdAt, 0)) AS newestPR
