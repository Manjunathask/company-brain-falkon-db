// Answers: search active non-bot maintainers by recent non-bulk authored commit activity.
// Parameters: $q is a case-insensitive login/name fragment; $since is an epoch-millisecond cutoff; $limit is 1..25.
// Shape: count distinct qualifying commits per active person, then rank prefix matches before contains matches.
MATCH (p:Person:Active)
WHERE coalesce(p.bot,false)=false
OPTIONAL MATCH (p)-[:AUTHORED]->(c:Commit)
WHERE c.ts >= $since AND coalesce(c.bulk,false)=false
WITH p, count(DISTINCT c) AS recentCommits
WITH p, recentCommits,
     CASE WHEN $q='' THEN 0
          WHEN toLower(coalesce(p.login,'')) STARTS WITH toLower($q)
            OR toLower(coalesce(p.name,'')) STARTS WITH toLower($q) THEN 0
          ELSE 1 END AS matchGroup,
     CASE WHEN $q='' OR toLower(coalesce(p.login,'')) STARTS WITH toLower($q)
            OR toLower(coalesce(p.name,'')) STARTS WITH toLower($q)
          OR toLower(coalesce(p.login,'')) CONTAINS toLower($q)
            OR toLower(coalesce(p.name,'')) CONTAINS toLower($q) THEN 1 ELSE 0 END AS matched
WHERE matched=1
RETURN p.login AS login, coalesce(p.name,p.login) AS name, recentCommits, p.lastSeen AS lastSeen, matchGroup
ORDER BY matchGroup, recentCommits DESC, login
LIMIT $limit
