Implemented the WP10 files and snapshot exporter. **The requested live verification is incomplete** because this environment has no Docker, `uv`, pytest, FalkorDB client, or reachable graph.

### Verification

- Snapshot integrity: passed. **1,728,785 bytes** (about 1.65 MiB); 2,240 commits, 3,602 PRs, 19 RFCs, 9 CODEOWNERS rules, 19 RFC issues, 220 identity mappings, and 4,427 HEAD paths.
- Query catalogue: all 77 query files have README entries.
- Python compilation and `git diff --check`: passed.
- `pytest`: not run; `python -m pytest -q` reports `No module named pytest`.
- Live graph rebuild/count comparison and throwaway graph cleanup: not run. No node/relationship comparison is available to report.

### Files changed

- Snapshot and container startup: [.gitignore](<(.gitignore>), [Dockerfile](<(Dockerfile>), [docker-compose.yml](<(docker-compose.yml>), [snapshot.py](<(src/busfactor/snapshot.py>), [bootstrap.py](<(src/busfactor/bootstrap.py>), plus snapshot support in the loader, decision linker, identity loader, and git ingestion.
- No-key chat response: [app.py](<(src/busfactor/api/app.py>) and [llm.py](<(src/busfactor/agent/llm.py>).
- Submission materials: [README.md](<(README.md>), [docs/DEMO.md](<(docs/DEMO.md>), [docs/BLOG.md](<(docs/BLOG.md>), [LICENSE](<(LICENSE>), and [docs/PROGRESS.md](<(docs/PROGRESS.md>).
- `data/snapshot/`: seven gzip input files and `manifest.json`.

### Docker verification for the reviewer

Run these from the repo root:

```sh
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8000/api/health
docker compose restart falkordb
curl http://127.0.0.1:8000/api/health
docker compose logs app
```

The restart check should show the graph still populated. The image tags, FalkorDB data path, and volume persistence could not be verified here. No commit was made.