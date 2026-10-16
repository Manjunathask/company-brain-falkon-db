// Answers: classify the departing person's recent Component expertise by the active experts who remain.
// Parameters: $login is the departing person; $since is the activity-window start in epoch milliseconds; $minCommits is the minimum remaining expertise; $componentPrefix optionally narrows component names; $includeTestResources includes fixture-only components when true.
// Shape: use Component KNOWS edges for the departing person, filter scope explicitly, and collect distinct qualified people in one optional match to avoid multiplying commit totals.
MATCH (gone:Person {login: $login})-[gk:KNOWS]->(component:Component)
WHERE gk.lastTouched > $since AND coalesce(gone.bot, false) = false
  AND ($componentPrefix = '' OR component.name STARTS WITH $componentPrefix)
  AND ($includeTestResources OR NOT component.name ENDS WITH '/(test-resources)')
OPTIONAL MATCH (other:Person:Active)-[ok:KNOWS]->(component)
WHERE other <> gone AND coalesce(other.bot, false) = false
  AND ok.lastTouched > $since AND ok.commits >= $minCommits
WITH component, gk, collect(DISTINCT other.login) AS remaining
RETURN component.name AS component,
       gk.commits AS theirCommits,
       size(remaining) AS expertsLeft,
       remaining,
       CASE size(remaining) WHEN 0 THEN 'ORPHANED' WHEN 1 THEN 'AT RISK' ELSE 'COVERED' END AS risk
ORDER BY CASE risk WHEN 'ORPHANED' THEN 0 WHEN 'AT RISK' THEN 1 ELSE 2 END,
         theirCommits DESC, component
