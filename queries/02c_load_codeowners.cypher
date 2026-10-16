// Answers: load declared CODEOWNERS handles and the modules covered by each rule.
// Parameters: $rows contains {pattern, module, owners}; owners has {login, handle} maps.
// Shape: normalized login is the stable Person key while the original spelling is retained as p.handle.
UNWIND $rows AS row
MERGE (m:Module {name: row.module})
WITH row, m
UNWIND row.owners AS owner
MERGE (p:Person {login: owner.login})
SET p.handle = coalesce(p.handle, owner.handle)
MERGE (p)-[:DECLARED_OWNER {pattern: row.pattern}]->(m)
