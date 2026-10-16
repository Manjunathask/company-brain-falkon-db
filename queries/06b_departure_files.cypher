// Answers: group files touched by a departing person that no other active, non-bot person touched recently.
// Parameters: $login is the departing person; $since is the activity-window start in epoch milliseconds.
// Shape: collect distinct other active editors per file before filtering, so multiple commits or files cannot inflate orphan counts and bots never count as coverage.
MATCH (gone:Person {login: $login})-[:AUTHORED]->(c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component:Component)
WHERE c.ts > $since AND coalesce(gone.bot, false) = false
WITH gone, f, component
OPTIONAL MATCH (other:Person:Active)-[:AUTHORED]->(otherCommit:Commit)-[:TOUCHED]->(f)
WHERE other <> gone AND otherCommit.ts > $since AND coalesce(other.bot, false) = false
WITH f, component, collect(DISTINCT other.login) AS otherEditors
WITH f, component, size(otherEditors) = 0 AS isOrphaned
WITH component,
     count(DISTINCT f) AS theirFiles,
     count(DISTINCT CASE WHEN isOrphaned THEN f ELSE null END) AS orphanedFiles,
     collect(DISTINCT CASE WHEN isOrphaned THEN f.path ELSE null END) AS examples
WHERE orphanedFiles > 0
RETURN component.name AS component,
       orphanedFiles,
       theirFiles,
       examples[0..5] AS examplePaths
ORDER BY orphanedFiles DESC, component
