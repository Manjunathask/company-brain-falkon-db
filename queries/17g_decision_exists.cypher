// Answers: whether an exact decision slug exists, regardless of outcome or supersession.
// Parameters: $slug is the exact Decision.slug.
// Shape: one indexed lookup separates a missing decision from missing qualifying evidence.
MATCH (d:Decision {slug: $slug})
RETURN d.slug AS slug, d.title AS title, d.status AS status
