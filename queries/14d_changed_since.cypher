// Answers: count and list commits and PRs connected to one supported graph entity since a timestamp.
// Parameters: $kind is person/component/module/decision; $key is its raw stable key; $since is epoch milliseconds.
// Shape: optional traversals retain a zero-result row; commit-to-PR links are collected after commit aggregation.
OPTIONAL MATCH (p:Person {login: $key})-[:AUTHORED]->(pc:Commit)
WHERE $kind = 'person' AND pc.ts > $since
OPTIONAL MATCH (p)-[:OPENED|REVIEWED]->(personPr:PR)
WHERE $kind = 'person' AND coalesce(personPr.mergedAt, personPr.createdAt, 0) > $since
OPTIONAL MATCH (c:Component {name: $key})<-[:IN_COMPONENT]-(:File)<-[:TOUCHED]-(cc:Commit)
WHERE $kind = 'component' AND cc.ts > $since
OPTIONAL MATCH (m:Module {name: $key})<-[:IN_MODULE]-(:File)<-[:TOUCHED]-(mc:Commit)
WHERE $kind = 'module' AND mc.ts > $since
OPTIONAL MATCH (d:Decision {slug: $key})<-[:IMPLEMENTS]-(decisionPr:PR)
WHERE $kind = 'decision' AND coalesce(decisionPr.mergedAt, decisionPr.createdAt, 0) > $since
WITH collect(DISTINCT pc) + collect(DISTINCT cc) + collect(DISTINCT mc) AS allCommits,
     collect(DISTINCT personPr) + collect(DISTINCT decisionPr) AS directPrs
WITH [x IN allCommits WHERE x IS NOT NULL] AS commits, [x IN directPrs WHERE x IS NOT NULL] AS directPrs
OPTIONAL MATCH (commit:Commit)-[:PART_OF]->(commitPr:PR)
WHERE commit IN commits
WITH commits, directPrs, collect(DISTINCT commitPr) AS linkedPrs
WITH commits, directPrs + linkedPrs AS allPrs
WITH commits, [x IN allPrs WHERE x IS NOT NULL] AS prs
RETURN size(commits) AS commitCount, size(prs) AS prCount,
       [x IN commits | {sha:x.sha, subject:x.subject, ts:x.ts}] AS commits,
       [x IN prs | {number:x.number, title:x.title, mergedAt:x.mergedAt}] AS prs
