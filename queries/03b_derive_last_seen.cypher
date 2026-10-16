// Answers: refresh each person's last commit/activity time and the Active label for the requested window; reviews count because maintainers can contribute without committing.
// Parameters: $since is the activity cutoff in epoch milliseconds.
// Shape: clear Active first, aggregate each activity source separately, then reduce the null-filtered timestamps to one latest value.
MATCH (p:Person)
REMOVE p:Active
WITH p
OPTIONAL MATCH (p)-[:AUTHORED]->(c:Commit)
WITH p, max(c.ts) AS lastCommit
OPTIONAL MATCH (p)-[:OPENED]->(pr:PR)
WITH p, lastCommit, max(pr.createdAt) AS lastOpenedPR
OPTIONAL MATCH (p)-[review:REVIEWED]->(:PR)
WITH p, lastCommit, lastOpenedPR, max(review.at) AS lastReview
OPTIONAL MATCH (p)-[comment:COMMENTED]->(:Issue)
WITH p, lastCommit, lastOpenedPR, lastReview, max(comment.at) AS lastComment
WITH p, lastCommit,
     reduce(latest = null, at IN [x IN [lastCommit, lastOpenedPR, lastReview, lastComment] WHERE x IS NOT NULL] |
       CASE WHEN latest IS NULL OR at > latest THEN at ELSE latest END) AS lastSeen
SET p.lastCommit = lastCommit, p.lastSeen = lastSeen
WITH p, lastSeen
WHERE lastSeen > $since AND coalesce(p.bot, false) = false
SET p:Active
