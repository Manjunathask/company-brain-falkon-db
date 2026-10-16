// Answers: return only the graph entities matched by find_entity, with no neighboring edges.
// Parameters: $people, $components, $modules, $decisions, and $files are matched keys.
// Shape: match each typed stable key and return the nodes as the UI selection evidence.
MATCH (n)
WHERE (n:Person AND n.login IN $people) OR (n:Component AND n.name IN $components)
   OR (n:Module AND n.name IN $modules) OR (n:Decision AND n.slug IN $decisions)
   OR (n:File AND n.path IN $files)
RETURN n AS node LIMIT 200
