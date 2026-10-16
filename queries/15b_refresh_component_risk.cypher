// Answers: classify current component risk from active, non-bot expertise.
// Parameters: $since is the activity-window start; run before and after refresh using the same Active labels.
// Shape: count distinct active experts per component and apply the departure risk thresholds.
MATCH (component:Component)
OPTIONAL MATCH (p:Person:Active)-[k:KNOWS]->(component)
WHERE coalesce(p.bot, false) = false AND k.lastTouched > $since
WITH component, collect(DISTINCT p.login) AS experts
RETURN component.name AS component, size(experts) AS expertsLeft,
       CASE size(experts) WHEN 0 THEN 'ORPHANED' WHEN 1 THEN 'AT RISK' ELSE 'COVERED' END AS risk
ORDER BY component
