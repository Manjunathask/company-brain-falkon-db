// Answers: calculate how many people cover half of recent commit expertise in each Component.
// Parameters: $since is the activity-window start in epoch milliseconds; $minCommits is the minimum person expertise; $minTotal is the minimum component commit total to report.
// Shape: rank each person's Component KNOWS count, collect the per-component totals, filter small components, then reduce in order until half the total is covered.
MATCH (p:Person)-[k:KNOWS]->(component:Component)
WHERE k.lastTouched > $since AND k.commits >= $minCommits AND coalesce(p.bot, false) = false
WITH component, p.login AS login, k.commits AS c
ORDER BY c DESC, login
WITH component, collect({login: login, c: c}) AS ranked, sum(c) AS total
WITH collect({component: component.name, ranked: ranked, total: total}) AS areas
WITH [area IN areas WHERE area.total >= $minTotal] AS reportable,
     size([area IN areas WHERE area.total < $minTotal]) AS filteredOut
UNWIND CASE WHEN size(reportable) = 0 THEN [null] ELSE reportable END AS area
RETURN area.component AS component,
       reduce(acc = {n: 0, s: 0}, x IN area.ranked |
         CASE WHEN acc.s * 2 >= area.total THEN acc ELSE {n: acc.n + 1, s: acc.s + x.c} END).n AS busFactor,
       area.ranked[0].login AS topExpert,
       toFloat(area.ranked[0].c) / area.total AS topShare,
       size(area.ranked) AS people,
       area.total AS total,
       filteredOut
ORDER BY busFactor, topShare DESC, component
