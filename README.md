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

## Built with AI assistance

Claude Code (reviewer/orchestrator) and OpenAI Codex (implementation) were used. Their task briefs
are in [docs/tasks/](docs/tasks/).
