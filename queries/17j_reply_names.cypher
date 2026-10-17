// Answers: which graph names the final reply should check against this turn's evidence.
// Parameters: none.
// Shape: union three small catalogues; omit bots and single-segment areas to reduce ordinary-word matches.
MATCH (p:Person) WHERE coalesce(p.bot, false) = false
RETURN 'person' AS kind, p.login AS name, p.name AS alias
UNION ALL
MATCH (c:Component) WHERE c.name CONTAINS '/'
RETURN 'component' AS kind, c.name AS name, c.name AS alias
UNION ALL
MATCH (d:Decision)
RETURN 'decision' AS kind, d.title AS name, d.slug AS alias
