// Answers: link loaded commits to any PR nodes whose numbers match Commit.pr.
// Parameters: none; the PR and Commit.pr properties must already be loaded.
// Shape: filter out null PR numbers first, then use the indexed PR.number equality lookup.
MATCH (c:Commit) WHERE c.pr IS NOT NULL
MATCH (pr:PR {number: c.pr})
MERGE (c)-[:PART_OF]->(pr)
