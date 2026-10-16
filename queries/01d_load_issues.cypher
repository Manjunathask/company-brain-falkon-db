// Answers: load the RFC tracking issues and people who opened or commented on them.
// Parameters: $rows has issue properties, author/login handle/bot fields, and commenters as {login, handle, bot} maps.
// Shape: Issue remains a separate label from PR despite GitHub's shared number space; a deleted/missing author uses GitHub's `ghost` placeholder. Comment rows carry handles and bot flags directly.
UNWIND $rows AS row
MERGE (i:Issue {number: row.number})
SET i.title = row.title, i.state = row.state, i.createdAt = row.createdAt
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
MERGE (p)-[:COMMENTED]->(i)
