// Answers: remove stale title-keyword-only IMPLEMENTS links before rebuilding curated matches.
// Parameters: none.
// Shape: delete only links whose sole recorded source is title-keyword; preserve links with stronger evidence.
MATCH ()-[r:IMPLEMENTS]->()
WHERE size(coalesce(r.sources,[]))=1 AND 'title-keyword' IN coalesce(r.sources,[])
DELETE r
