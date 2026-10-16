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

The graph model and the Cypher query rationale are documented in [docs/PLAN.md](docs/PLAN.md).

## Built with AI assistance

Claude Code (reviewer/orchestrator) and OpenAI Codex (implementation) were used. Their task briefs
are in [docs/tasks/](docs/tasks/).
