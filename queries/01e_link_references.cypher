// Answers: connect PRs to referenced RFC issues that are already represented in the graph.
// Parameters: $rows contains {pr, issue} number pairs extracted from PR bodies.
// Shape: MATCH on Issue intentionally avoids creating ordinary GitHub issues beyond the curated RFC set.
UNWIND $rows AS row
MATCH (pr:PR {number: row.pr})
MATCH (i:Issue {number: row.issue})
MERGE (pr)-[:REFERENCES]->(i)
