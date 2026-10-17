// Answers: which RFC decisions a successor must preserve in one code area, with their sources and who else took part.
// Parameters: $login is the leaving person; $component is the Component.name.
// Shape: find decisions linked to the area through Commit -PART_OF-> PR -IMPLEMENTS-> Decision (all loaded history) or an RFC document filed in the area, then count explicit and title-match PRs per decision before adding sources, participants and any SUPERSEDED_BY reason.
// Order: explicit PR links first, then title matches; at most 5 decisions.
MATCH (area:Component {name:$component})
OPTIONAL MATCH (area)<-[:IN_COMPONENT]-(:File)<-[:TOUCHED]-(:Commit)-[:PART_OF]->(:PR)-[:IMPLEMENTS]->(linked:Decision)
WITH area, collect(DISTINCT linked) AS viaPRs
OPTIONAL MATCH (area)<-[:IN_COMPONENT]-(:File)<-[:DOCUMENTED_IN]-(documented:Decision)
WITH area, viaPRs, collect(DISTINCT documented) AS viaDocuments
WITH area, viaPRs + viaDocuments AS found
UNWIND found AS d
WITH DISTINCT area, d
OPTIONAL MATCH (area)<-[:IN_COMPONENT]-(:File)<-[:TOUCHED]-(:Commit)-[:PART_OF]->(pr:PR)-[link:IMPLEMENTS]->(d)
WITH d, pr, max(CASE WHEN link.confidence = 'high' THEN 1 ELSE 0 END) AS explicit
WITH d, toInteger(sum(explicit)) AS explicitPRs, count(DISTINCT pr) AS areaPRs
OPTIONAL MATCH (d)-[:TRACKED_IN]->(issue:Issue)
OPTIONAL MATCH (d)-[:DOCUMENTED_IN]->(doc:File)
WITH d, explicitPRs, areaPRs, issue, doc
OPTIONAL MATCH (:Person {login:$login})-[gp:PARTICIPATED_IN]->(d)
WHERE gp.confidence = 'high'
WITH d, explicitPRs, areaPRs, issue, doc, count(gp) > 0 AS leavingParticipated
OPTIONAL MATCH (other:Person:Active)-[op:PARTICIPATED_IN]->(d)
WHERE other.login <> $login AND coalesce(other.bot,false)=false AND op.confidence = 'high'
WITH d, explicitPRs, areaPRs, issue, doc, leavingParticipated, collect(DISTINCT other.login) AS others
OPTIONAL MATCH (d)-[newerLink:SUPERSEDED_BY]->(newer:Decision)
OPTIONAL MATCH (older:Decision)-[olderLink:SUPERSEDED_BY]->(d)
WITH d, explicitPRs, areaPRs - explicitPRs AS titleMatchPRs, issue, doc, leavingParticipated, others,
     coalesce(newerLink.rationale, olderLink.rationale) AS rationale,
     coalesce(newerLink.rationaleSource, olderLink.rationaleSource) AS rationaleSource,
     CASE WHEN newer IS NOT NULL THEN 'replaced by ' + newer.title
          WHEN older IS NOT NULL THEN 'replaces ' + older.title END AS supersession
ORDER BY explicitPRs DESC, titleMatchPRs DESC, d.title
LIMIT 5
RETURN d.title AS title, d.slug AS slug, d.status AS status, explicitPRs, titleMatchPRs,
       issue.number AS issue, doc.path AS rfcPath, leavingParticipated,
       size(others) AS otherActiveCount, others[0..5] AS otherActive, rationale, rationaleSource, supersession
