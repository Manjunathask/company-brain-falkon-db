// Answers: count code changes since accepted decisions were made and identify editors who did not participate.
// Parameters: $minConfidence defaults to 'high'; only implementations at or above the threshold are included.
// Shape: collect qualifying decision participants and linked files, then count later edits and outside editors.
MATCH (d:Decision {status:'accepted'})<-[impl:IMPLEMENTS]-(implementingPR:PR)
WHERE impl.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
OPTIONAL MATCH (insider:Person)-[part:PARTICIPATED_IN]->(d)
WHERE part.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
WITH d, collect(DISTINCT insider) AS insiders, collect(DISTINCT implementingPR) AS implementingPRs
UNWIND implementingPRs AS implementingPR
MATCH (implementingPR)<-[:PART_OF]-(:Commit)-[:TOUCHED]->(f:File)
WITH d, insiders, collect(DISTINCT f) AS files
UNWIND files AS f
MATCH (f)<-[:TOUCHED]-(later:Commit)<-[:AUTHORED]-(p:Person)
WHERE later.ts > d.decidedOn AND coalesce(p.bot,false)=false
RETURN d.title AS decision, count(DISTINCT later) AS changesSinceDecision,
       count(DISTINCT CASE WHEN p IN insiders THEN null ELSE p END) AS editorsOutsideDecision
ORDER BY changesSinceDecision DESC, decision
