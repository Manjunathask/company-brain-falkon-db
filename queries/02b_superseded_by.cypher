// Answers: record that Managed Commits was superseded by Catalog-Managed Tables.
// Parameters: none.
// Shape: stable decision slugs and MERGE make this evidence edge safe to rerun.
MATCH (old:Decision {slug: 'managed-commits'}), (new:Decision {slug: 'catalog-managed'})
MERGE (old)-[s:SUPERSEDED_BY]->(new)
SET s.source = 'PR #4382'
