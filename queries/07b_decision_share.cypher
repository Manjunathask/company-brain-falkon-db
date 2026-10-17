// Answers: report a person's share of implementing PRs, split into explicit evidence and title-only keyword guesses.
// Parameters: $login, $minShare (combined share), $minConfidence ('high' or 'low').
// Shape: deduplicate per PR/decision before counting; any high-confidence edge wins over a low edge for that PR.
// Aggregate ownership before co-openers; sort explicit share first without changing combined-share filtering.
MATCH (person:Person {login:$login})-[:OPENED]->(theirPR:PR)-[theirLink:IMPLEMENTS]->(decision:Decision)
WHERE ($minConfidence = 'low' OR theirLink.confidence = 'high')
WITH person, decision, theirPR, max(CASE WHEN theirLink.confidence = 'high' THEN 1 ELSE 0 END) AS explicit
WITH person, decision, count(DISTINCT theirPR) AS theirPRs, toInteger(sum(explicit)) AS theirExplicitPRs
MATCH (allPR:PR)-[link:IMPLEMENTS]->(decision)
WHERE ($minConfidence = 'low' OR link.confidence = 'high')
WITH person, decision, theirPRs, theirExplicitPRs, allPR,
     max(CASE WHEN link.confidence = 'high' THEN 1 ELSE 0 END) AS explicit
WITH person, decision, theirPRs, theirExplicitPRs, count(DISTINCT allPR) AS totalPRs, toInteger(sum(explicit)) AS explicitPRs
OPTIONAL MATCH (other:Person:Active)-[:OPENED]->(otherPR:PR)-[otherLink:IMPLEMENTS]->(decision)
WHERE other <> person AND ($minConfidence = 'low' OR otherLink.confidence = 'high')
WITH decision, theirPRs, theirExplicitPRs, totalPRs, explicitPRs, other, count(DISTINCT otherPR) AS otherPRCount
WITH decision, theirPRs, theirExplicitPRs, totalPRs, explicitPRs,
     collect(CASE WHEN other IS NULL THEN null ELSE {login:other.login, prs:otherPRCount} END) AS openers
WITH decision, theirPRs, theirExplicitPRs, totalPRs, explicitPRs, openers, toFloat(theirPRs) / totalPRs AS share,
     CASE WHEN explicitPRs = 0 THEN 0.0 ELSE toFloat(theirExplicitPRs) / explicitPRs END AS explicitShare
WHERE share >= $minShare
RETURN decision.title AS decision, decision.status AS status,
       theirPRs, totalPRs, share, theirExplicitPRs, explicitPRs,
       theirPRs - theirExplicitPRs AS theirTitleMatchPRs, totalPRs - explicitPRs AS titleMatchPRs,
       openers AS otherOpeners
ORDER BY explicitShare DESC, share DESC, decision
