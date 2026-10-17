// Answers: calculate how many people cover half of qualifying in-window commits in each Component.
// Parameters: $since is the activity-window start in epoch milliseconds; $minCommits is the minimum in-window commits per person; $minTotal is the minimum component commit total; $includeTestResources includes fixture-only components when true.
// Shape: KNOWS.commits covers all loaded history, so count distinct in-window commits per person/area before ranking.
// Ranking: rank each person's qualifying commit count, exclude test resources by default, collect per-component totals, then reduce in order until half the total is covered.
MATCH (p:Person)-[:AUTHORED]->(commit:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(component:Component)
WHERE commit.ts > $since AND coalesce(p.bot, false) = false
  AND coalesce(commit.bulk, false) = false AND coalesce(f.exists, true) = true
  AND ($includeTestResources OR NOT component.name ENDS WITH '/(test-resources)')
WITH component, p, count(DISTINCT commit) AS c
WHERE c >= $minCommits
WITH component, p.login AS login, c
ORDER BY c DESC, login
WITH component, collect({login: login, c: c}) AS ranked, sum(c) AS total
WITH collect({component: component.name, ranked: ranked, total: total}) AS areas
WITH [area IN areas WHERE area.total >= $minTotal] AS reportable,
     size([area IN areas WHERE area.total < $minTotal]) AS filteredOut
UNWIND CASE WHEN size(reportable) = 0 THEN [null] ELSE reportable END AS area
WITH area, filteredOut, reduce(acc = {n: 0, s: 0}, x IN area.ranked |
         CASE WHEN acc.s * 2 >= area.total THEN acc ELSE {n: acc.n + 1, s: acc.s + x.c} END).n AS busFactor
RETURN area.component AS component, busFactor,
       [person IN area.ranked[0..busFactor] | person.login] AS countedExperts,
       area.ranked[0].login AS topExpert,
       toFloat(area.ranked[0].c) / area.total AS topShare,
       size(area.ranked) AS people,
       area.total AS total,
       filteredOut
ORDER BY busFactor, topShare DESC, component
