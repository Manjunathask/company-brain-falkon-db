// Answers: load people, commits, touched files, modules, and components from local git history.
// Parameters: $rows is a batch of commit maps with author, authorEmail, authorHandle, authorBot, authorName, files, and commit fields; each file has module and component.
// Shape: UNWIND plus MERGE makes each batch safe to replay; Module remains first-path-segment and Component adds finer-grained ownership.
UNWIND $rows AS c
MERGE (p:Person {login: c.author})
SET p.emails = CASE
      WHEN c.authorEmail IN coalesce(p.emails, []) THEN coalesce(p.emails, [])
      ELSE coalesce(p.emails, []) + [c.authorEmail]
    END,
    p.name = coalesce(p.name, c.authorName),
    p.handle = coalesce(p.handle, c.authorHandle),
    p.bot = coalesce(p.bot, false) OR c.authorBot
MERGE (k:Commit {sha: c.sha})
SET k.ts = c.ts, k.subject = c.subject, k.area = c.area, k.pr = c.pr
MERGE (p)-[:AUTHORED]->(k)
WITH k, c
UNWIND c.files AS f
MERGE (fl:File {path: f.path})
WITH k, c, f, fl
OPTIONAL MATCH (fl)-[oldComponent:IN_COMPONENT]->(:Component)
DELETE oldComponent
WITH k, c, f, fl
MERGE (m:Module {name: f.module})
MERGE (fl)-[:IN_MODULE]->(m)
MERGE (component:Component {name: f.component})
MERGE (fl)-[:IN_COMPONENT]->(component)
MERGE (component)-[:IN_MODULE]->(m)
MERGE (k)-[t:TOUCHED]->(fl)
SET t.added = f.added, t.deleted = f.deleted
