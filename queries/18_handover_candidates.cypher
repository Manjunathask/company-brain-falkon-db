// Answers: who could take over one code area from a leaving person, with each kind of evidence in its own column.
// Parameters: $login is the leaving person; $component is the Component.name; $since is the activity-window start (epoch ms); $exclude lists logins marked unavailable in team memory; $limit caps the rows.
// Shape: collect the leaving person's in-window files and PRs here first, then build the candidate pool from recent authors and recent reviewers of this area, then aggregate each evidence column in its own WITH stage with count(DISTINCT ...) so columns cannot multiply.
// Order: reviewedTheirPRs, sharedFiles, areaCommits, areaReviews, login, with no weights. A candidate who already reviewed this person's PRs here has seen these changes, so that ranks first. Excluded people are returned last with skipped = true so the packet can say why they were left out.
MATCH (gone:Person {login:$login})-[:AUTHORED]->(gc:Commit)-[:TOUCHED]->(gf:File)-[:IN_COMPONENT]->(area:Component {name:$component})
WHERE gc.ts > $since AND coalesce(gc.bulk,false)=false AND coalesce(gf.exists,true)=true
WITH gone, area, collect(DISTINCT gf) AS theirFiles, collect(DISTINCT gc) AS theirCommits
OPTIONAL MATCH (tc:Commit)-[:PART_OF]->(theirPR:PR)
WHERE tc IN theirCommits
WITH gone, area, theirFiles, collect(DISTINCT theirPR) AS theirPRs
// Files only the leaving person edited here in the window: the candidate's "still to learn" list.
UNWIND theirFiles AS tf
OPTIONAL MATCH (other:Person:Active)-[:AUTHORED]->(oc:Commit)-[:TOUCHED]->(tf)
WHERE other <> gone AND coalesce(other.bot,false)=false AND oc.ts > $since AND coalesce(oc.bulk,false)=false
WITH gone, area, theirFiles, theirPRs, tf, count(DISTINCT other) AS otherEditors
WITH gone, area, theirFiles, theirPRs, collect(CASE WHEN otherEditors = 0 THEN tf ELSE null END) AS soloFiles
// Decisions linked to this area: through PRs whose commits touched it, or an RFC document filed in it.
OPTIONAL MATCH (area)<-[:IN_COMPONENT]-(:File)<-[:TOUCHED]-(:Commit)-[:PART_OF]->(:PR)-[:IMPLEMENTS]->(linked:Decision)
WITH gone, area, theirFiles, theirPRs, soloFiles, collect(DISTINCT linked) AS linkedDecisions
OPTIONAL MATCH (area)<-[:IN_COMPONENT]-(:File)<-[:DOCUMENTED_IN]-(documented:Decision)
WITH gone, area, theirFiles, theirPRs, soloFiles, linkedDecisions, collect(DISTINCT documented) AS documentedDecisions
WITH gone, area, theirFiles, theirPRs, soloFiles, linkedDecisions + documentedDecisions AS areaDecisions
// Candidate pool: recent authors here, plus recent reviewers of PRs that touched here.
OPTIONAL MATCH (author:Person:Active)-[:AUTHORED]->(ac:Commit)-[:TOUCHED]->(af:File)-[:IN_COMPONENT]->(area)
WHERE author <> gone AND coalesce(author.bot,false)=false
  AND ac.ts > $since AND coalesce(ac.bulk,false)=false AND coalesce(af.exists,true)=true
WITH gone, area, theirFiles, theirPRs, soloFiles, areaDecisions, collect(DISTINCT author) AS authors
OPTIONAL MATCH (reviewer:Person:Active)-[rv:REVIEWED]->(:PR)<-[:PART_OF]-(rc:Commit)-[:TOUCHED]->(rf:File)-[:IN_COMPONENT]->(area)
WHERE reviewer <> gone AND coalesce(reviewer.bot,false)=false AND rv.at > $since
  AND rc.ts > $since AND coalesce(rc.bulk,false)=false AND coalesce(rf.exists,true)=true
WITH gone, area, theirFiles, theirPRs, soloFiles, areaDecisions, authors, collect(DISTINCT reviewer) AS reviewers
UNWIND authors + [r IN reviewers WHERE NOT r IN authors] AS cand
OPTIONAL MATCH (cand)-[r1:REVIEWED]->(p1:PR)
WHERE p1 IN theirPRs
WITH area, theirFiles, theirPRs, soloFiles, areaDecisions, cand, count(DISTINCT p1) AS reviewedTheirPRs
OPTIONAL MATCH (cand)-[:AUTHORED]->(c2:Commit)-[:TOUCHED]->(f2:File)
WHERE f2 IN theirFiles AND c2.ts > $since AND coalesce(c2.bulk,false)=false
WITH area, theirFiles, theirPRs, soloFiles, areaDecisions, cand, reviewedTheirPRs, count(DISTINCT f2) AS sharedFiles
OPTIONAL MATCH (cand)-[:AUTHORED]->(c3:Commit)-[:TOUCHED]->(f3:File)-[:IN_COMPONENT]->(area)
WHERE c3.ts > $since AND coalesce(c3.bulk,false)=false AND coalesce(f3.exists,true)=true
WITH area, theirFiles, theirPRs, soloFiles, areaDecisions, cand, reviewedTheirPRs, sharedFiles,
     count(DISTINCT c3) AS areaCommits
OPTIONAL MATCH (cand)-[r4:REVIEWED]->(p4:PR)<-[:PART_OF]-(c4:Commit)-[:TOUCHED]->(f4:File)-[:IN_COMPONENT]->(area)
WHERE r4.at > $since AND c4.ts > $since AND coalesce(c4.bulk,false)=false AND coalesce(f4.exists,true)=true
WITH theirFiles, theirPRs, soloFiles, areaDecisions, cand, reviewedTheirPRs, sharedFiles, areaCommits,
     count(DISTINCT p4) AS areaReviews
OPTIONAL MATCH (cand)-[pi:PARTICIPATED_IN]->(d:Decision)
WHERE pi.confidence = 'high' AND d IN areaDecisions
WITH theirFiles, theirPRs, soloFiles, cand, reviewedTheirPRs, sharedFiles, areaCommits, areaReviews,
     collect(DISTINCT d.title) AS sharedDecisions
OPTIONAL MATCH (cand)-[:AUTHORED]->(:Commit)-[:TOUCHED]->(known:File)
WHERE known IN soloFiles
WITH theirFiles, theirPRs, soloFiles, cand, reviewedTheirPRs, sharedFiles, areaCommits, areaReviews, sharedDecisions,
     collect(DISTINCT known) AS knownSolo
WITH cand.login AS login, cand.name AS name, cand.login IN $exclude AS skipped,
     reviewedTheirPRs, size(theirPRs) AS theirPRCount, sharedFiles, size(theirFiles) AS outOf,
     areaCommits, areaReviews, sharedDecisions,
     [f IN soloFiles WHERE NOT f IN knownSolo | f.path][0..5] AS toLearn
ORDER BY skipped, reviewedTheirPRs DESC, sharedFiles DESC, areaCommits DESC, areaReviews DESC, login
LIMIT $limit
RETURN login, name, skipped, reviewedTheirPRs, theirPRCount, sharedFiles, outOf, areaCommits, areaReviews,
       sharedDecisions, toLearn
