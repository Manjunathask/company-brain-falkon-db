// Answers: show the departing person, affected Components, and active experts who remain.
// Parameters: $login and $components are the departing person and returned Component names.
// Shape: return one KNOWS path from the departing person and one from each active remaining expert for every affected Component.
CALL {
  MATCH p=(gone:Person {login:$login})-[:KNOWS]->(component:Component)
  WHERE component.name IN $components
  RETURN p
  UNION
  MATCH p=(other:Person:Active)-[:KNOWS]->(component:Component)
  WHERE component.name IN $components AND other.login <> $login AND coalesce(other.bot,false)=false
  RETURN p
}
RETURN p LIMIT 200
