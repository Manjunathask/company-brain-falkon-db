// Answers: how much work landed in one code area after a saved handover packet, to explain why a new packet differs.
// Parameters: $component is the Component.name; $since is the saved packet's time (epoch ms).
// Shape: count distinct non-bulk commits on current files in the area after $since, and the distinct PRs those commits belong to.
MATCH (c:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(:Component {name:$component})
WHERE c.ts > $since AND coalesce(c.bulk,false)=false AND coalesce(f.exists,true)=true
OPTIONAL MATCH (c)-[:PART_OF]->(pr:PR)
RETURN count(DISTINCT c) AS commits, count(DISTINCT pr) AS prs
