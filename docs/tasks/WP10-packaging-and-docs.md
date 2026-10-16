<task>
You are implementing work package WP10 of "Bus Factor" (Graph Hacks, FalkorDB): make it easy for judges to run, and
write the submission docs. Read AGENTS.md, docs/PLAN.md, docs/PROGRESS.md, docs/QUERIES.md, README.md and
docs/eval/. Everything before is committed. The submission needs: public repo, README with setup steps and the graph
data model, the Cypher queries the product depends on, a demo video (the developer records it), a live deployment or
full local setup steps, and the tracks entered (03 Company Brain, 02 Agent Memory and Coordination).

Build:
1. Data snapshot so judges need no GitHub token: `python -m busfactor.snapshot export` writes data/snapshot/ with
   gzip-compressed JSON of the parsed inputs the loaders read (git_log, rfcs, codeowners, prs, rfc_issues,
   identities, head file list) plus a manifest (counts, git HEAD sha, export time). `load all --from-snapshot`
   (and refresh-free derive/link) rebuilds the graph from it. data/snapshot/ is committed (un-ignore it in
   .gitignore); everything else under data/ stays ignored. Keep the snapshot small (gzip; report its size).
   All of it is public GitHub data; say so in the manifest.
2. Docker: a Dockerfile for the app (python:3.12-slim, uv, non-root user) and a docker-compose service `app` that
   waits for FalkorDB, loads the snapshot if the `delta` graph is empty (one-shot, idempotent), and serves the API on
   127.0.0.1:8000. ANTHROPIC_API_KEY / ANTHROPIC_WORKSPACE_ID / AGENT_MODEL are passed through from the host
   environment; without a key the app still serves the departure simulator and direct tools, and /api/ask returns a
   clear "set ANTHROPIC_API_KEY" message. Pin image tags. FALKORDB_HOST=falkordb inside compose.
3. README rewrite (keep it readable, no marketing voice):
   - What it is (two sentences) and the headline question.
   - Quick start: `docker compose up` (with and without an Anthropic key); local dev setup with uv as the second path;
     how to rebuild from live GitHub data (token, refresh).
   - Graph model: a Mermaid diagram of node labels and relationships (including Component, Active, bulk/exists flags,
     IMPLEMENTS confidence, PARTICIPATED_IN, KNOWS, WORKS_WITH, the mem_<user> and mem_team graphs) and a table of
     labels and keys.
   - How answers are produced: agent -> tools -> one Cypher file each -> evidence graph; FalkorDB features used
     (Cypher, full-text index, algo.betweenness, algo.WCC, GRAPH.COPY what-if, GRAPH.RO_QUERY read-only tools).
   - Query catalogue: a table linking every queries/*.cypher file to what it answers (link docs/QUERIES.md for the
     long explanations).
   - Tracks entered and how each is met (03: people/code/decisions/ownership; 02: per-user memory, shared team memory,
     watcher agent, changed-since recall).
   - Data quality decisions (bulk commits, deleted files, bots, identity merge, title-keyword confidence) in a short list.
   - Model choice with the eval numbers from docs/eval.
   - "Built with AI assistance": Claude Code (Claude Opus 5.5) reviewed and orchestrated, OpenAI Codex implemented; every
     task brief, Codex report and review round is in docs/tasks/; the agent itself calls Claude Sonnet 5.5 at runtime.
   - License: add an MIT LICENSE file (ask nothing; the reviewer will confirm with the developer).
4. docs/DEMO.md: a 3-minute demo script with exact clicks and questions (departure simulator for scottsand-db and
   murali-db, one chat question with the "How I know" Cypher trail, decision trace for an icebergcompat file, the
   refresh + team memory moment, memory recall in a second session). Use only numbers the live graph produces now
   (run the tools to get them) and mark them as "as of <date>".
5. docs/BLOG.md: a draft blog post (800-1100 words) for the side prize: the problem, why a graph, the model, three
   queries explained, what we learned (the data-quality findings and the reviewer/implementer workflow), honest limits.
6. Append to docs/PROGRESS.md.
</task>

<action_safety>
Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/ or data/delta. Do not run git commit. No live LLM calls.
Never put secrets into the image, compose file or snapshot. Your sandbox has no network: you cannot pull images; write
the Dockerfile and compose changes and say what the reviewer must run to verify them.
</action_safety>

<verification_loop>
pytest must pass. Export the snapshot, drop and rebuild a throwaway graph from it (e.g. FALKORDB_GRAPH=delta_snapcheck),
compare node and relationship counts per label/type with the live `delta` graph, then delete the throwaway graph.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; snapshot size and the count comparison; the commands the reviewer must run for Docker;
anything uncertain.
</compact_output_contract>
