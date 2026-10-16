// Answers: derive recent collaboration between non-bot people from files both edited.
// Parameters: $since is the epoch-millisecond window start, $minShared is the minimum shared files, and $maxFileCommits excludes hub files touched by too many commits in that window.
// Shape: delete old edges first for an exact rerun; current files and non-bulk commits only prevent deleted paths and mass edits from creating false collaboration.
OPTIONAL MATCH ()-[old:WORKS_WITH]->()
DELETE old
WITH count(old) AS cleared
MATCH (c:Commit)-[:TOUCHED]->(f:File)
WHERE c.ts > $since AND coalesce(c.bulk, false) = false AND coalesce(f.exists, true) = true
WITH f, count(DISTINCT c) AS fileCommits
WHERE fileCommits <= $maxFileCommits
WITH collect(f) AS usefulFiles
UNWIND usefulFiles AS f
MATCH (a:Person)-[:AUTHORED]->(c1:Commit)-[:TOUCHED]->(f)<-[:TOUCHED]-(c2:Commit)<-[:AUTHORED]-(b:Person)
WHERE id(a) < id(b)
AND c1.ts > $since AND c2.ts > $since
  AND coalesce(c1.bulk, false) = false AND coalesce(c2.bulk, false) = false
  AND coalesce(a.bot, false) = false AND coalesce(b.bot, false) = false
WITH a, b, count(DISTINCT f) AS shared
WHERE shared >= $minShared
MERGE (a)-[w:WORKS_WITH]->(b)
SET w.sharedFiles = shared
