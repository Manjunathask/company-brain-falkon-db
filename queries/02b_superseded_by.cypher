// Answers: record that one decision was superseded by another, with the evidence and the stated reason.
// Parameters: $old and $new are Decision slugs; $source names the evidence (PR #4382 for Managed Commits -> Catalog-Managed Tables); $rationale is a verbatim excerpt of the replacing decision's tracking issue, or null; $rationaleSource names that issue.
// Shape: stable decision slugs and MERGE make this evidence edge safe to rerun; the rationale is parsed at load time, not generated.
MATCH (old:Decision {slug: $old}), (new:Decision {slug: $new})
MERGE (old)-[s:SUPERSEDED_BY]->(new)
SET s.source = $source, s.rationale = $rationale, s.rationaleSource = $rationaleSource
