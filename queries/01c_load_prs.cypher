// Answers: load GitHub pull requests and their opener/reviewer people.
// Parameters: $rows has PR properties, author/login handle/bot fields, and reviewers as {login, handle, bot, at} maps.
// Shape: stable MERGE keys make replay safe; missing GitHub authors are represented by the normalized `ghost` placeholder. Reviewer timestamps retain the latest submittedAt value across replays.
UNWIND $rows AS row
MERGE (pr:PR {number: row.number})
SET pr.title = row.title, pr.state = row.state, pr.createdAt = row.createdAt,
    pr.updatedAt = coalesce(row.updatedAt, row.mergedAt, row.createdAt),
    pr.mergedAt = row.mergedAt, pr.body = row.body
WITH pr, row
MERGE (author:Person {login: row.author})
SET author.handle = coalesce(author.handle, row.authorHandle),
    author.bot = coalesce(author.bot, false) OR row.authorBot
MERGE (author)-[:OPENED]->(pr)
WITH pr, row
UNWIND row.reviewers AS r
MERGE (p:Person {login: r.login})
SET p.handle = coalesce(p.handle, r.handle),
    p.bot = coalesce(p.bot, false) OR r.bot
MERGE (p)-[review:REVIEWED]->(pr)
SET review.at = CASE
  WHEN r.at IS NULL THEN review.at
  WHEN review.at IS NULL OR r.at > review.at THEN r.at
  ELSE review.at
END
