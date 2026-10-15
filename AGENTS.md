# Bus Factor: a company brain for Delta Lake, on FalkorDB

Hackathon entry for **Graph Hacks** (WeMakeDevs × FalkorDB), 15–18 Oct 2026.
Submissions close **Sun 18 Oct, 11:59 PM IST**; aim to submit Sunday evening.
Tracks entered: **03 Company Brain** (main) and **02 Agent Memory and Coordination**.

This file is the shared brief for every coding agent on this project (Codex reads it directly;
Claude Code reads it through `CLAUDE.md`). Edit this file, not `CLAUDE.md`.

The full plan, graph model and all 13 Cypher queries are in `docs/PLAN.md`. Read it before
starting any task. What has been done so far is in `docs/PROGRESS.md`.

## What we are building

A graph of the public `delta-io/delta` repository (people, commits, files, modules, PRs,
issues, RFC decisions) in FalkorDB, plus an agent that answers questions by traversing it.
The headline demo: **"What does the project lose if this maintainer leaves?"** The agent reports
orphaned modules, decisions with nobody left who took part, and the best successor for each area,
showing the graph path behind every answer.

## Hard rules (from the hackathon; breaking these disqualifies the entry)

1. **FalkorDB is the product, not decoration.** Every answer must come from a Cypher query or a
   FalkorDB graph algorithm. Do not add a vector store or a parallel SQL/pandas path that
   answers the same questions. If the app still works with FalkorDB removed, the graph counts as decoration and the entry fails.
2. **Public data only.** Only `delta-io/delta` (and optionally a FalkorDB repo) from GitHub.
   Never load anything from a private or login-protected source.
3. **All code is new work, written from 15 Oct onward.** Do not copy code from other projects.
   General libraries are fine.
4. **AI assistance must be disclosed.** Keep the "Built with AI assistance" section of README.md current.
5. **I must be able to explain everything.** The judges can ask about the graph model, any query,
   and the architecture. So:
   - keep every Cypher query in its own `.cypher` file with a header comment saying what it
     answers, its parameters, and why it is shaped that way;
   - prefer plain, readable code over clever abstractions; no framework that hides the Cypher;
   - after writing a query, explain it to me in two or three sentences.

## Stack

- Python 3.11+, managed with `uv`.
- FalkorDB in Docker via `docker-compose.yml`: port 6379 (database) and 3000 (FalkorDB Browser UI).
  Use a named volume for data. The docs disagree on the data path (`/data` vs
  `/var/lib/falkordb/data`), so check the image and confirm persistence survives a restart.
- Python client: the official `falkordb` package (confirm the name and API on docs.falkordb.com).
- GitHub data: GraphQL API with a token from the `GITHUB_TOKEN` env var. **Cache every raw API
  response under `data/raw/`** (gitignored) so re-runs never re-hit the API.
- Agent LLM (Friday): not chosen yet. Keep it behind one small interface so the provider is swappable.
- UI (Saturday): not chosen yet. It must be able to draw a returned path as a small graph.

## Suggested layout

```
Hackathon/   (repo root)
  AGENTS.md  CLAUDE.md  README.md  docker-compose.yml  pyproject.toml  .env.example
  docs/PLAN.md  docs/PROGRESS.md
  queries/            # one file per query: 01_load_commits.cypher, 05_bus_factor.cypher, ...
  src/busfactor/
    db.py             # connection + run_query(name, params) that loads queries/<name>.cypher
    ingest/           # git_log.py, github_api.py, rfcs.py, codeowners.py
    derive.py         # runs the derive queries (KNOWS, WORKS_WITH, PARTICIPATED_IN, Active)
    agent/            # Friday
    api/              # Saturday
  tests/
  data/               # gitignored: raw API cache, the delta clone
```

## Facts about the data (checked on 14 Oct; re-check if anything looks off)

- Window: the last two years of `delta-io/delta`. About 2,236 commits from 218 author emails.
- Commit subjects end with `(#N)`, the PR number, in 2,233 of 2,236 recent commits. Use it for `PART_OF`.
- Subjects start with an area tag: `[Spark]`, `[Kernel]`, `[kernel-spark]`, `[UniForm]`, `[Flink]`, ...
  Case varies (`[Spark]` and `[SPARK]`), so lower-case the tag before storing it.
- Module = first path segment: `spark`, `kernel`, `connectors`, `flink`, `python`, `storage`,
  `iceberg`, `sharing`, `protocol_rfcs`, `docs`, ... Root-level files go to a `root` module.
- Decisions: `protocol_rfcs/README.md` has three markdown tables (Proposed, Accepted, Rejected)
  listing 19 RFCs with dates, the RFC file path and the GitHub issue URL. Parse these; no LLM needed.
- Managed Commits (rejected) was superseded by Catalog-Managed Tables. The evidence is the
  commit message of PR #4382. Store it as `SUPERSEDED_BY {source: 'PR #4382'}`.
- Commit messages almost never cite RFC issue numbers. Link PRs to decisions through **PR bodies**
  (high confidence) or the feature name in the PR title (low confidence). Match keywords on word
  boundaries: a bare `ICT` also matches "conflict" and "dict".
- `.github/CODEOWNERS` gives declared owners per path (GitHub handles).
- Identity: map git author emails to GitHub logins with the API's commit author `login`. For
  emails with no match, use the key `email:<address>` rather than guessing.

## FalkorDB gotchas

- An unreferenced relationship in a pattern is only checked for existence, so path counts can be
  wrong. Always aggregate with `count(DISTINCT x)`.
- `LIMIT` does not limit eager operations (CREATE / MERGE / SET); they run fully first.
- Indexes are not used for `<>` filters.
- Aggregates are not allowed inside pattern comprehensions; aggregate in a `WITH` first.
- Algorithms: `CALL algo.betweenness({nodeLabels: [...], relationshipTypes: [...]}) YIELD node, score`,
  `CALL algo.WCC({...}) YIELD node, componentId`, `CALL algo.pageRank('Label', 'REL') YIELD node, score`.
- Cypher cannot query across graphs. The per-user memory graphs (`mem_<login>`) join to the
  `delta` graph by `Entity.key` in Python.
- If a long derive query hits the server timeout, raise it with `FALKORDB_ARGS="TIMEOUT <ms>"`.

## How to work

- Small steps. After each loader or query, run it and print node and relationship counts or
  sample rows so I can check them before moving on.
- All loads are idempotent (`MERGE` on stable keys, batches of about 500 with `UNWIND`).
  Re-running any step must be safe.
- Commit after each working step with a clear message.
- Do not start on the agent or the UI before the graph is loaded and the derive queries
  return sensible numbers.

## Working alongside another agent

Claude Code and Codex may both work in this repo, but never on the same files at the same time.

- Before starting, read `docs/PROGRESS.md` and `git log --oneline -10`.
- Work only on the task you were given. If it touches files another agent is changing, stop and ask.
- When you finish a step, add one line to `docs/PROGRESS.md` (date, agent, what changed, what to check)
  and commit. Name the agent in the commit message, e.g. `[codex] add CODEOWNERS loader`.
- If you change a query in `queries/`, re-run it and record the new counts in `PROGRESS.md`.

## Schedule

| Day | Goal |
| --- | --- |
| Thu 15 Oct, evening | Docker + FalkorDB; load commits, files, modules, PRs, RFC decisions, CODEOWNERS; run derive; check the queries flagged in PLAN.md |
| Fri 16 Oct, evening | Agent with the Cypher queries and graph algorithms as tools; PR → Decision linking |
| Sat 17 Oct | Departure simulator, memory graph, UI showing the path behind each answer |
| Sun 18 Oct | Deploy, README (setup, graph model, queries, AI disclosure), demo video, blog post, submit |
