// Answers: list a person's active, non-bot direct WORKS_WITH collaborators before departure.
// Parameters: $login is the person being simulated.
// Shape: traverse the undirected collaboration edge and deduplicate neighbor logins for the reported count.
MATCH (:Person {login:$login})-[:WORKS_WITH]-(other:Person:Active)
WHERE coalesce(other.bot,false)=false
RETURN collect(DISTINCT other.login) AS directCollaborators
