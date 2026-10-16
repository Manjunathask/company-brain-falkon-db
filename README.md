# Bus Factor

Bus Factor builds a company brain for the public Delta Lake repository using FalkorDB. The demo
will show what project knowledge is exposed when a maintainer leaves, with graph paths behind
each answer.

## Setup so far

1. Install Python 3.11+, `uv`, and Docker.
2. Run `uv sync` and copy `.env.example` to `.env`.
3. Start FalkorDB with `docker compose up -d`.
4. Clone Delta Lake with `git clone -c core.longpaths=true https://github.com/delta-io/delta.git data/delta`.
5. Run the local parsers with `uv run python -m busfactor.ingest.git_log`,
   `uv run python -m busfactor.ingest.rfcs`, and `uv run python -m busfactor.ingest.codeowners`.
6. Load parsed data with `uv run python -m busfactor.load all` once FalkorDB is running.
7. Link PRs to RFC decisions with `uv run python -m busfactor.link_decisions`.
8. Refresh derived relationships with `uv run python -m busfactor.derive`.

## Pipeline

Load all source data first (`busfactor.load all`), then run `busfactor.link_decisions`, then
`busfactor.derive`. The decision linker creates high-confidence issue-reference and RFC-document
links plus low-confidence title-keyword links. Low-confidence PR links still contribute
`PARTICIPATED_IN` evidence when someone opened or reviewed the PR; the relationship copies the
link confidence so later queries can filter to high-confidence participation.

The graph model and the Cypher query rationale are documented in [docs/PLAN.md](docs/PLAN.md).

## Graph model

A Component is a finer-grained code area beneath a Module, assigned from source package paths or the first two directory segments for nested paths; file-only paths are grouped under a `(files)` bucket and test resources under `(test-resources)`. It exists to reveal concentrated expertise and orphaned files inside large modules such as `spark`.

## Agent

Ask a graph question with `uv run python -m busfactor.agent ask "What if huan233usc leaves?" --user <github-login>`. Configure `AGENT_PROVIDER=anthropic` (default) with `ANTHROPIC_API_KEY` (and `ANTHROPIC_WORKSPACE_ID` if your key is not scoped to a workspace); `AGENT_MODEL` defaults to `claude-sonnet-5-5` and `AGENT_EFFORT` to `medium`. Why Sonnet at medium: on five demo questions it took 69 s and $0.37 in total, against 112 s and $1.17 for Opus 5.5 with the same conclusions; low effort gave up on one ambiguous question (results and script in [docs/eval/](docs/eval/)). Set `AGENT_PROVIDER=scripted` and `AGENT_SCRIPT` to a JSON list of steps for deterministic, no-network runs. The loop calls FalkorDB tools and returns the tool trail and merged graph evidence with the answer.

## Run the app

Start FalkorDB, load the public Delta graph, and run the local API and browser UI:

```powershell
docker compose up -d
uv run python -m busfactor.load all
uv run python -m busfactor.link_decisions
uv run python -m busfactor.derive
uv run python -m busfactor.api
```

FalkorDB is reached at `127.0.0.1` by default, not `localhost`: Docker publishes the port on IPv4 loopback, and on Windows a `localhost` connection tries IPv6 first and costs about 2 s per new connection.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API binds to `127.0.0.1` by default; set `HOST` and `PORT` to override it. The browser only calls this local API; FalkorDB credentials and any model API key stay on the server. Each answer includes the graph evidence and the Cypher for every tool call under “How I know”. The Departure simulator combines the collaboration what-if, component exposure, orphaned files, decision share, and successor evidence in one panel.

## Memory (Track 02)

Each user has a separate `mem_<login>` FalkorDB graph. Questions are recorded as session episodes linked to the Delta entities the graph tools touched, and explicit user corrections are stored with their source. Later sessions recall related questions and corrections, then query the Delta graph for changes since the last time an entity was discussed; memory never edits the Delta graph.

## Built with AI assistance

Claude Code (reviewer/orchestrator) and OpenAI Codex (implementation) were used. Their task briefs
are in [docs/tasks/](docs/tasks/).
