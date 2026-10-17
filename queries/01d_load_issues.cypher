// Answers: load the RFC tracking issues and people who opened or commented on them.
// Parameters: $rows has issue properties (title, state, createdAt, body), author/login handle/bot fields, and commenters as {login, handle, bot, at} maps.
// Shape: Issue remains a separate label from PR despite GitHub's shared number space; a deleted/missing author uses GitHub's `ghost` placeholder. Comment timestamps retain the latest createdAt value across replays.
UNWIND $rows AS row
MERGE (i:Issue {number: row.number})
SET i.title = row.title, i.state = row.state, i.createdAt = row.createdAt, i.body = row.body
WITH i, row
MERGE (author:Person {login: row.author})
SET author.handle = coalesce(author.handle, row.authorHandle),
    author.bot = coalesce(author.bot, false) OR row.authorBot
MERGE (author)-[:OPENED]->(i)
WITH i, row
UNWIND row.commenters AS c
MERGE (p:Person {login: c.login})
SET p.handle = coalesce(p.handle, c.handle),
    p.bot = coalesce(p.bot, false) OR c.bot
MERGE (p)-[comment:COMMENTED]->(i)
SET comment.at = CASE
  WHEN c.at IS NULL THEN comment.at
  WHEN comment.at IS NULL OR c.at > comment.at THEN c.at
  ELSE comment.at
END
