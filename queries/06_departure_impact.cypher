// Answers: report areas with 2+ (or $minCommits) recent commits by the leaving person, remaining authors, and separate review evidence.
// Parameters: $login, $since (epoch ms), $minCommits (both author sides), $componentPrefix, $includeTestResources.
// Shape: KNOWS.commits is all-history, so count distinct in-window non-bulk commits on current files per person/area.
// Aggregate remaining authors before reviewers; reviews never change the author risk code.
// reviewerPRs pairs each listed reviewer with the number of this area's in-window PRs they reviewed.
MATCH (gone:Person {login: $login})-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component:Component)
WHERE c.ts > $since AND coalesce(gone.bot, false) = false
  AND coalesce(c.bulk, false) = false AND coalesce(f.exists, true) = true
  AND ($componentPrefix = '' OR component.name STARTS WITH $componentPrefix)
  AND ($includeTestResources OR NOT component.name ENDS WITH '/(test-resources)')
WITH gone, component, count(DISTINCT c) AS theirCommits
WHERE theirCommits >= $minCommits
OPTIONAL MATCH (other:Person:Active)-[:AUTHORED]->(oc:Commit)-[:TOUCHED]->(of:File)-[:IN_COMPONENT]->(component)
WHERE other <> gone AND coalesce(other.bot, false) = false
  AND oc.ts > $since AND coalesce(oc.bulk, false) = false AND coalesce(of.exists, true) = true
WITH gone, component, theirCommits, other, count(DISTINCT oc) AS otherCommits
ORDER BY otherCommits DESC, other.login
WITH gone, component, theirCommits,
     collect(CASE WHEN otherCommits >= $minCommits THEN other.login ELSE null END) AS remaining
OPTIONAL MATCH (reviewer:Person:Active)-[review:REVIEWED]->(pr:PR)<-[:PART_OF]-(rc:Commit)-[:TOUCHED]->(rf:File)-[:IN_COMPONENT]->(component)
WHERE reviewer <> gone AND coalesce(reviewer.bot, false) = false AND review.at > $since
  AND rc.ts > $since AND coalesce(rc.bulk, false) = false AND coalesce(rf.exists, true) = true
WITH component, theirCommits, remaining, reviewer, count(DISTINCT pr) AS reviewedPRs
ORDER BY reviewedPRs DESC, reviewer.login
WITH component, theirCommits, remaining,
     collect(CASE WHEN reviewer IS NULL THEN null ELSE {login: reviewer.login, prs: reviewedPRs} END) AS allReviewers
RETURN component.name AS component, theirCommits, size(remaining) AS expertsLeft, remaining,
       [r IN allReviewers[0..5] | r.login] AS reviewers, allReviewers[0..5] AS reviewerPRs,
       size(allReviewers) AS reviewerCount,
       CASE size(remaining) WHEN 0 THEN 'NO OTHER AUTHOR' WHEN 1 THEN 'ONE OTHER AUTHOR' ELSE 'COVERED' END AS risk
ORDER BY expertsLeft, reviewerCount, theirCommits DESC, component
