// Answers: show the paths behind one handover packet: the leaving person's reading PRs, their decision links, candidate reviews of those PRs, and authorship of the area.
// Parameters: $login is the leaving person; $component is the Component.name; $prs are the reading-list PR numbers; $candidates are the listed candidate logins.
// Shape: union of short paths only (no Commit or File nodes), so the evidence graph stays readable; KNOWS is the all-history authorship edge.
CALL {
  MATCH p=(gone:Person {login:$login})-[:OPENED]->(pr:PR)
  WHERE pr.number IN $prs
  RETURN p
  UNION
  MATCH p=(pr:PR)-[:IMPLEMENTS]->(:Decision)
  WHERE pr.number IN $prs
  RETURN p
  UNION
  MATCH p=(candidate:Person)-[:REVIEWED]->(pr:PR)
  WHERE candidate.login IN $candidates AND pr.number IN $prs
  RETURN p
  UNION
  MATCH p=(person:Person)-[:KNOWS]->(:Component {name:$component})
  WHERE person.login = $login OR person.login IN $candidates
  RETURN p
}
RETURN p
