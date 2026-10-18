// Answers: load people, commits, touched files, modules, and components from local git history.
// Parameters: $rows is a batch of commit maps with author, authorEmail, authorHandle, authorBot, authorName, files, and commit fields; each file has module, component, and exists.
// Shape: UNWIND plus MERGE makes each batch safe to replay; HEAD existence distinguishes deleted history from current knowledge while preserving TOUCHED.
// Memory: MERGE/DELETE make the query eager, so every file row is held at once. Rows carry only k, f and fl, never c:
// carrying c copied each commit's whole file list onto every one of its file rows (a 1,150-file commit made ~1.3M
// file maps), and the snapshot load peaked at 681 MB instead of 51 MB.
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
WITH k, c.files AS files
UNWIND files AS f
MERGE (fl:File {path: f.path})
SET fl.exists = coalesce(f.exists, fl.exists, true)
WITH k, f, fl
OPTIONAL MATCH (fl)-[oldComponent:IN_COMPONENT]->(:Component)
DELETE oldComponent
WITH k, f, fl
MERGE (m:Module {name: f.module})
MERGE (fl)-[:IN_MODULE]->(m)
MERGE (component:Component {name: f.component})
MERGE (fl)-[:IN_COMPONENT]->(component)
MERGE (component)-[:IN_MODULE]->(m)
MERGE (k)-[t:TOUCHED]->(fl)
SET t.added = f.added, t.deleted = f.deleted
