// Answers: resolve free text to people, modules, Components, decisions, or files using graph indexes and string matching.
// Parameters: $text is the case-insensitive query string; $limit caps results per entity type.
// Shape: match stable identifiers and case-folded names/titles, then union typed candidates into one ranked result list.
WITH $text AS text
CALL { WITH text MATCH (p:Person) WHERE toLower(p.login)=toLower(text) OR toLower(coalesce(p.name,'')) CONTAINS toLower(text) RETURN 'person' AS kind, p.login AS key, coalesce(p.name,p.login) AS label, 1.0 AS score
 UNION ALL WITH text MATCH (m:Module) WHERE toLower(m.name) CONTAINS toLower(text) RETURN 'module' AS kind, m.name AS key, m.name AS label, 1.0 AS score
 UNION ALL WITH text MATCH (c:Component) WHERE toLower(c.name) CONTAINS toLower(text) RETURN 'component' AS kind, c.name AS key, c.name AS label, 1.0 AS score
 UNION ALL WITH text MATCH (d:Decision) WHERE toLower(d.slug) CONTAINS toLower(text) OR toLower(d.title) CONTAINS toLower(text) RETURN 'decision' AS kind, d.slug AS key, d.title AS label, 1.0 AS score
 UNION ALL WITH text CALL db.idx.fulltext.queryNodes('Decision', text) YIELD node, score RETURN 'decision' AS kind, node.slug AS key, node.title AS label, score AS score
 UNION ALL WITH text MATCH (f:File) WHERE toLower(f.path) ENDS WITH toLower(text) RETURN 'file' AS kind, f.path AS key, f.path AS label, 1.0 AS score
}
WITH kind,key,label,max(score) AS score
ORDER BY score DESC, key
WITH kind, collect({key:key,label:label,score:score})[0..$limit] AS hits
UNWIND hits AS hit
RETURN kind, hit.key AS key, hit.label AS label, hit.score AS score
ORDER BY kind, score DESC, key
