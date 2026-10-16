## Files created or changed

- `.env.example`, `docker-compose.yml`, `README.md`
- `src/busfactor/db.py`, `src/busfactor/load.py`
- `src/busfactor/ingest/{__init__,git_log,identity,rfcs,codeowners}.py`
- `queries/{00_indexes,01_load_commits,01b_link_part_of,02_load_decisions,02b_superseded_by,03_load_codeowners}.cypher`
- `tests/test_ingest.py`, `docs/tasks/wp1.md`, and one entry in `docs/PROGRESS.md`
- The parsers generated gitignored `data/raw/git_log.json`, `data/raw/rfcs.json`, and `data/raw/codeowners.json`.

The commit query upserts people, commits, files, modules, and their authorship and touch relationships; `01b` adds commit-to-PR links after PR nodes exist. The decision query links RFC decisions to issues and files, while the supersession and CODEOWNERS queries add their evidence and owner relationships; the index file keeps each index statement independently runnable.

## Verification

- Pytest: `5 passed in 0.58s`
- Git log: `Commits: 2234`; `Distinct author emails: 220`; `Distinct files: 4445`; `Commits with PR number: 2231`
- RFC parser: `RFCs: 19 (proposed=11, accepted=7, rejected=1)`
- CODEOWNERS parser: `Rules: 9`

## Decisions for review

- Pinned `falkordb/falkordb:v4.10.0` for reproducible runs. The image tag and mounted data path still need confirmation when Docker is available.
- RFC `proposedOn` and `decidedOn` are both stored as epoch milliseconds, consistent with the plan’s timestamp convention.
- Module summaries count distinct commits touching each module, including commits touching multiple files in the same module only once.

## Still undone or uncertain

- FalkorDB loading was not run because Docker and the database are not available yet. Confirm the container’s data path and persistence after restart.
- `part_of` has no matching PR nodes until the GitHub PR loader is implemented and run.

**Needs:** No additional dependencies. User action: install/start Docker, then verify the image data path and persistence.