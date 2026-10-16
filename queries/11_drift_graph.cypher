// Answers: show accepted-decision implementation paths and later edits on the files behind them.
// Parameters: $decisions are selected titles; $minConfidence is the implementation threshold.
// Shape: return both Decision-to-File implementation paths and later Commit paths on those same files, capped at 200.
CALL {
  MATCH p=(d:Decision)<-[impl:IMPLEMENTS]-(pr:PR)<-[:PART_OF]-(:Commit)-[:TOUCHED]->(:File)
  WHERE d.title IN $decisions AND impl.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
  RETURN p
  UNION
  MATCH p=(d:Decision)<-[impl:IMPLEMENTS]-(pr:PR)<-[:PART_OF]-(:Commit)-[:TOUCHED]->(f:File)<-[:TOUCHED]-(later:Commit)
  WHERE d.title IN $decisions AND impl.confidence IN CASE WHEN $minConfidence='high' THEN ['high'] ELSE ['high','low'] END
    AND later.ts > d.decidedOn
  RETURN p
}
RETURN p LIMIT 200
