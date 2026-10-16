// Answers: load RFC decisions, their tracking issues, and RFC document files.
// Parameters: $rows is a batch of RFC maps with slug, title, status, proposedOn, decidedOn, issue, path, and module.
// Shape: MERGE on stable identifiers makes nodes and edges safe to recreate on reruns.
UNWIND $rows AS r
MERGE (d:Decision {slug: r.slug})
SET d.title = r.title, d.status = r.status, d.proposedOn = r.proposedOn, d.decidedOn = r.decidedOn
MERGE (i:Issue {number: r.issue})
MERGE (d)-[:TRACKED_IN]->(i)
MERGE (f:File {path: r.path})
MERGE (m:Module {name: r.module})
MERGE (f)-[:IN_MODULE]->(m)
MERGE (d)-[:DOCUMENTED_IN]->(f)
