// Answers: show recent file-to-decision evidence paths, including how each PR was linked to the decision.
// Parameters: $path is the exact File.path; $limit is the maximum paths.
// Shape: traverse File <- Commit -> PR -> Decision -> Issue; return readable node properties alongside the path for graph rendering.
MATCH p=(f:File {path:$path})<-[:TOUCHED]-(c:Commit)-[:PART_OF]->(pr:PR)-[impl:IMPLEMENTS]->(d:Decision)-[:TRACKED_IN]->(issue:Issue)
RETURN p, f.path AS file, c.sha AS commitSha, c.ts AS commitTs,
       pr.number AS prNumber, pr.title AS prTitle,
       d.slug AS decisionSlug, d.title AS decisionTitle, d.status AS decisionStatus,
       impl.confidence AS confidence, impl.via AS via, issue.number AS issueNumber
ORDER BY CASE impl.confidence WHEN 'high' THEN 0 ELSE 1 END, commitTs DESC
LIMIT $limit
