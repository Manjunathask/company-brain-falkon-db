### Files created or changed

- Added [github_api.py](/C:/Users/skman/Documents/Hackathon/src/busfactor/ingest/github_api.py), with cached GraphQL fetching, pagination, parsers, bot detection, and reference extraction.
- Added [01c_load_prs.cypher](/C:/Users/skman/Documents/Hackathon/queries/01c_load_prs.cypher), [01d_load_issues.cypher](/C:/Users/skman/Documents/Hackathon/queries/01d_load_issues.cypher), and [01e_link_references.cypher](/C:/Users/skman/Documents/Hackathon/queries/01e_link_references.cypher).
- Updated [load.py](/C:/Users/skman/Documents/Hackathon/src/busfactor/load.py) with `prs`, `issues`, and `references` steps and the requested `all` order.
- Added GitHub response fixtures and tests in [test_github_api.py](/C:/Users/skman/Documents/Hackathon/tests/test_github_api.py).
- Added the WP2 entry to [PROGRESS.md](/C:/Users/skman/Documents/Hackathon/docs/PROGRESS.md).

The PR query loads PRs and opener/reviewer people, preserving original handles while using normalized logins as keys. The issue query loads RFC issues as separate `Issue` nodes, despite GitHub sharing number space with PRs. The reference query matches existing Issue nodes before linking them, so it only creates links to issues already loaded.

### Verification

- `.venv/Scripts/python -m pytest -q`: **11 passed in 0.56s**
- `.venv/Scripts/python -m busfactor.ingest.github_api all`: exited with `GITHUB_TOKEN not set (set it in .env or the environment)`, without a traceback.
- `git diff --check`: passed.

### Estimated full-run API use

Roughly **55–125+ GraphQL requests**: 5 identity batches, about 30–45 PR pages, up to 56 batches for referenced PRs outside the fetched window, and 19 issue requests plus any comment pages. A rough cost is **55–125+ points**, but nested reviews and comments can raise query costs; each cached response includes GitHub’s reported `rateLimit.cost` and `remaining`.

### Reviewer checks and uncertainties

- Validate the GraphQL query shapes against the live API, especially `repository.issue(number:)`, alias batching, and nested review cost. No live API or FalkorDB run was possible here.
- Confirm the real PR pagination boundary and count of referenced PRs needing the older-PR pass.
- Confirm the API rate-limit cost for review and comment connections from the cached live responses.

**Needs:** a `GITHUB_TOKEN` in `.env` or the environment for the reviewer’s live fetch, followed by loading into FalkorDB to check real counts.