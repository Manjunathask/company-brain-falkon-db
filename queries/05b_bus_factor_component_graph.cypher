// Answers: show exactly the authors counted toward each reported Component bus factor.
// Parameters: $areas contains {name, countedExperts} from the table.
// Shape: reuse the table's in-window ranking; KNOWS is an all-history evidence edge, never re-ranked here.
UNWIND $areas AS area
UNWIND area.countedExperts AS login
MATCH p=(person:Person {login:login})-[:KNOWS]->(areaNode:Component {name:area.name})
RETURN p
