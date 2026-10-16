// Answers: load PR number and title pairs for the curated decision keyword matcher.
// Parameters: none.
// Shape: read the PR identity and title fields used by the local matcher.
MATCH (pr:PR) RETURN pr.number AS number,pr.title AS title
