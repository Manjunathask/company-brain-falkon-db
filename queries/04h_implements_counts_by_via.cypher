// Answers: count IMPLEMENTS edges by evidence source.
// Parameters: none.
// Shape: aggregate implementation relationships by their via property.
MATCH ()-[r:IMPLEMENTS]->() RETURN r.via AS via,count(r) AS count ORDER BY via
