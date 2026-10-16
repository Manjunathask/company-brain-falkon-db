// Answers: load people, commits, touched files, and their modules from local git history.
// Parameters: $rows is a batch of commit maps with author, authorEmail, authorHandle, authorName, files, and commit fields.
// Shape: UNWIND plus MERGE makes each batch safe to replay; PART_OF is deferred until PRs exist.
UNWIND $rows AS c
MERGE (p:Person {login: c.author})
SET p.emails = CASE
      WHEN c.authorEmail IN coalesce(p.emails, []) THEN coalesce(p.emails, [])
      ELSE coalesce(p.emails, []) + [c.authorEmail]
    END,
    p.name = coalesce(p.name, c.authorName),
    p.handle = coalesce(p.handle, c.authorHandle)
MERGE (k:Commit {sha: c.sha})
SET k.ts = c.ts, k.subject = c.subject, k.area = c.area, k.pr = c.pr
MERGE (p)-[:AUTHORED]->(k)
WITH k, c
UNWIND c.files AS f
MERGE (fl:File {path: f.path})
MERGE (m:Module {name: f.module})
MERGE (fl)-[:IN_MODULE]->(m)
MERGE (k)-[t:TOUCHED]->(fl)
SET t.added = f.added, t.deleted = f.deleted
