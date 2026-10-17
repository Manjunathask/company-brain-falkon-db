// Answers: whether a login is an active, non-bot person, and their display name.
// Parameters: $login is the GitHub login (or email: key).
// Shape: one indexed lookup; the API returns 404 when no row comes back.
MATCH (p:Person:Active {login: $login})
WHERE coalesce(p.bot, false) = false
RETURN p.login AS login, p.name AS name
