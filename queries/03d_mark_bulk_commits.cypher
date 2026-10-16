// Answers: mark commits that touched more than the configured number of files as bulk changes.
// Parameters: $maxCommitFiles is the maximum touched-file count eligible for expertise and overlap derivation.
// Shape: reset every Commit first, then count distinct TOUCHED files and mark only commits above the cutoff; AUTHORED, TOUCHED, and decision paths remain intact.
MATCH (c:Commit)
SET c.bulk = false
WITH count(c) AS reset
MATCH (c:Commit)-[:TOUCHED]->(f:File)
WITH c, count(DISTINCT f) AS files
SET c.bulk = files > $maxCommitFiles
RETURN c.sha AS sha, files, c.subject AS subject
ORDER BY files DESC, sha
