// Answers: show the PR-opening paths behind decision-share ownership and the active co-openers to ask.
// Parameters: $login is the owner being evaluated; $decisions are returned decision titles; $minConfidence is the confidence threshold.
// Shape: return only person-to-PR-to-decision paths, restricted to the selected owner and active other openers at the same confidence threshold.
MATCH p=(person:Person)-[:OPENED]->(pr:PR)-[link:IMPLEMENTS]->(decision:Decision)
WHERE decision.title IN $decisions
  AND (person.login = $login OR 'Active' IN labels(person))
  AND ($minConfidence = 'low' OR link.confidence = 'high')
RETURN p LIMIT 200
