// Answers: calculate how many people cover half of qualifying in-window commits in each Module.
// Parameters: $since is the activity-window start in epoch milliseconds; $minCommits is the minimum in-window commits per person; $minTotal is the minimum module commit total to report.
// Shape: KNOWS.commits covers all loaded history, so count distinct in-window commits per person/area before ranking.
// Ranking: rank each person's qualifying commit count, collect the per-module totals, filter small modules, then reduce in order until half the total is covered.
MATCH (p:Person)-[:AUTHORED]->(commit:Commit)-[:TOUCHED]->(f:File)-[:IN_MODULE]->(m:Module)
WHERE commit.ts > $since AND coalesce(p.bot, false) = false
  AND coalesce(commit.bulk, false) = false AND coalesce(f.exists, true) = true
WITH m, p, count(DISTINCT commit) AS c
WHERE c >= $minCommits
WITH m, p.login AS login, c
ORDER BY c DESC, login
WITH m, collect({login: login, c: c}) AS ranked, sum(c) AS total
WITH collect({module: m.name, ranked: ranked, total: total}) AS areas
WITH [area IN areas WHERE area.total >= $minTotal] AS reportable,
     size([area IN areas WHERE area.total < $minTotal]) AS filteredOut
UNWIND CASE WHEN size(reportable) = 0 THEN [null] ELSE reportable END AS area
WITH area, filteredOut, reduce(acc = {n: 0, s: 0}, x IN area.ranked |
         CASE WHEN acc.s * 2 >= area.total THEN acc ELSE {n: acc.n + 1, s: acc.s + x.c} END).n AS busFactor
RETURN area.module AS module, busFactor,
       [person IN area.ranked[0..busFactor] | person.login] AS countedExperts,
       area.ranked[0].login AS topExpert,
       toFloat(area.ranked[0].c) / area.total AS topShare,
       size(area.ranked) AS people,
       area.total AS total,
       filteredOut
ORDER BY busFactor, topShare DESC, module
