// Answers: load RFC decisions, their tracking issues, and RFC document files.
// Parameters: $rows is a batch of RFC maps with slug, title, status, proposedOn, decidedOn, issue, path, module, and component.
// Shape: MERGE on stable identifiers makes nodes and edges safe to recreate on reruns; RFC document files join the same Component hierarchy as git-touched files.
UNWIND $rows AS r
MERGE (d:Decision {slug: r.slug})
SET d.title = r.title, d.status = r.status, d.proposedOn = r.proposedOn, d.decidedOn = r.decidedOn
MERGE (i:Issue {number: r.issue})
MERGE (d)-[:TRACKED_IN]->(i)
MERGE (f:File {path: r.path})
SET f.exists = coalesce(f.exists, true)
WITH d, i, r, f
OPTIONAL MATCH (f)-[oldComponent:IN_COMPONENT]->(:Component)
DELETE oldComponent
WITH d, i, r, f
MERGE (m:Module {name: r.module})
MERGE (f)-[:IN_MODULE]->(m)
MERGE (component:Component {name: r.component})
MERGE (f)-[:IN_COMPONENT]->(component)
MERGE (component)-[:IN_MODULE]->(m)
MERGE (d)-[:DOCUMENTED_IN]->(f)
