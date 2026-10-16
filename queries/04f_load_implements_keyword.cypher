// Answers: load low-confidence title keyword links from the curated Python matcher.
// Parameters: $rows contains {pr, slug, pattern} matches.
// Shape: MATCH avoids creating missing entities; MERGE makes loading replay-safe, while high-confidence evidence is never downgraded.
UNWIND $rows AS row
MATCH (pr:PR {number: row.pr})
MATCH (d:Decision {slug: row.slug})
MERGE (pr)-[r:IMPLEMENTS]->(d)
SET r.sources = CASE WHEN 'title-keyword' IN coalesce(r.sources, []) THEN coalesce(r.sources, []) ELSE coalesce(r.sources, []) + 'title-keyword' END,
    r.via = CASE WHEN r.confidence = 'high' AND r.via IS NOT NULL THEN r.via ELSE 'title-keyword' END,
    r.confidence = CASE WHEN r.confidence = 'high' THEN 'high' ELSE 'low' END
