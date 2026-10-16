// Answers: show declared owners and the top three observed experts for each reported Module.
// Parameters: $areas contains {name, actualTop3}; $modules are the returned Module names.
// Shape: return the Module-to-owner DECLARED_OWNER paths and Module-to-expert KNOWS paths for exactly the displayed top three.
CALL {
  MATCH p=(owner:Person)-[:DECLARED_OWNER]->(m:Module)
  WHERE m.name IN $modules
  RETURN p
  UNION
  UNWIND $areas AS area
  UNWIND area.actualTop3 AS login
  MATCH p=(person:Person {login:login})-[:KNOWS]->(m:Module {name:area.name})
  RETURN p
}
RETURN p LIMIT 200
