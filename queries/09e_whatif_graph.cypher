// Answers: show the departing person, their direct collaborators, and people cut off from the largest surviving group.
// Parameters: $people is the set of login keys selected by the simulation.
// Shape: return only WORKS_WITH edges whose two endpoints are in the evidence set, capped at 200.
MATCH (p:Person) WHERE p.login IN $people
OPTIONAL MATCH (p)-[r:WORKS_WITH]-(q:Person)
WHERE q.login IN $people
RETURN p AS n,r,q AS m LIMIT 200
