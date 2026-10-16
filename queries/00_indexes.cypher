// Answers: prepare stable lookup keys for every node type loaded in this package.
// Parameters: none.
// Shape: one idempotent index statement per line so the client can run them individually.
CREATE INDEX FOR (p:Person) ON (p.login)
CREATE INDEX FOR (c:Commit) ON (c.sha)
CREATE INDEX FOR (f:File) ON (f.path)
CREATE INDEX FOR (m:Module) ON (m.name)
CREATE INDEX FOR (pr:PR) ON (pr.number)
CREATE INDEX FOR (i:Issue) ON (i.number)
CREATE INDEX FOR (d:Decision) ON (d.slug)
