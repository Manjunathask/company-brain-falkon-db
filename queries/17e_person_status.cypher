// Answers: whether a login belongs to any Person, including inactive people and bots.
// Parameters: $login is the exact Person.login.
// Shape: one indexed lookup; inspect labels only after the active non-bot lookup misses.
MATCH (p:Person {login: $login})
RETURN p.login AS login, p.name AS name, 'Active' IN labels(p) AS active,
       coalesce(p.bot, false) AS bot, p.lastSeen AS lastSeen
