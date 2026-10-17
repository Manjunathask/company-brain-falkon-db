// Answers: whether a code area (Component) with this exact name exists.
// Parameters: $component is the Component.name.
// Shape: one lookup; the API returns 404 when no row comes back.
MATCH (c:Component {name: $component})
RETURN c.name AS component
