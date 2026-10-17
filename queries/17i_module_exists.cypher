// Answers: whether a correction refers to an existing Module.
// Parameters: $name is the exact Module.name.
// Shape: one indexed lookup validates the memory key without writing to either graph.
MATCH (m:Module {name: $name})
RETURN m.name AS name
