// Answers: show top bridge people, their WORKS_WITH neighbors, and the relationships among those nodes.
// Parameters: $people contains the top betweenness logins.
// Shape: expand from ranked people by one collaboration edge and cap the returned evidence at 200 edges.
MATCH (p:Person) WHERE p.login IN $people
OPTIONAL MATCH (p)-[r:WORKS_WITH]-(q:Person)
RETURN p AS n,r,q AS m LIMIT 200
