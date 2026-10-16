// Answers: remove Component nodes left without any File membership after a path-rule update.
// Parameters: none.
// Shape: aggregate optional File memberships, then delete only empty components so the graph contains no stale component names after replay.
MATCH (component:Component)
OPTIONAL MATCH (:File)-[membership:IN_COMPONENT]->(component)
WITH component, count(membership) AS files
WHERE files = 0
DETACH DELETE component
