// Answers: return the three most recent PR implementations for one decision.
// Parameters: $slug is the Decision slug.
// Shape: traverse IMPLEMENTS relationships, ordered by merge time and PR number.
MATCH (pr:PR)-[r:IMPLEMENTS]->(:Decision {slug:$slug})
RETURN pr.number AS number,pr.title AS title,pr.mergedAt AS mergedAt,r.via AS via,r.confidence AS confidence
ORDER BY mergedAt DESC,number DESC LIMIT 3
