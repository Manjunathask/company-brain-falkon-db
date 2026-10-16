// Answers: find decisions where this person opened a meaningful share of confidence-qualified implementing PRs, and list active co-openers to ask.
// Parameters: $login is the person; $minShare defaults to 0.3; $minConfidence is 'high' or 'low'.
// Shape: count distinct PRs at each step so duplicate edges cannot inflate ownership; issue commenters do not count as PR ownership.
MATCH (person:Person {login:$login})-[:OPENED]->(theirPR:PR)-[theirLink:IMPLEMENTS]->(decision:Decision)
WHERE ($minConfidence = 'low' OR theirLink.confidence = 'high')
WITH person, decision, count(DISTINCT theirPR) AS theirPRs
MATCH (allPR:PR)-[link:IMPLEMENTS]->(decision)
WHERE ($minConfidence = 'low' OR link.confidence = 'high')
WITH person, decision, theirPRs, count(DISTINCT allPR) AS totalPRs
OPTIONAL MATCH (other:Person:Active)-[:OPENED]->(otherPR:PR)-[otherLink:IMPLEMENTS]->(decision)
WHERE other <> person AND ($minConfidence = 'low' OR otherLink.confidence = 'high')
WITH person, decision, theirPRs, totalPRs, other, count(DISTINCT otherPR) AS otherPRCount
WITH decision, theirPRs, totalPRs,
     collect(CASE WHEN other IS NULL THEN null ELSE {login:other.login, prs:otherPRCount} END) AS openers
WITH decision, theirPRs, totalPRs, openers, toFloat(theirPRs) / totalPRs AS share
WHERE share >= $minShare
RETURN decision.title AS decision, decision.status AS status,
       theirPRs, totalPRs, share, openers AS otherOpeners
ORDER BY share DESC, decision
