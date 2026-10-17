## Files changed

- Added incremental refresh and shared memory: [refresh.py](../../src/busfactor/refresh.py), [team_memory.py](../../src/busfactor/team_memory.py), and updates to agent recall, GitHub PR parsing, and the API.
- Added refresh and team memory queries; updated PR loading and changed-since queries.
- Added the Ask-tab team memory list, updated README memory guidance, and documented the queries and progress.
- Added fixture refresh coverage, team memory integration coverage, and an `/api/team` contract test.

## Verification

- `pytest`: **62 passed**.
- `git diff --check`: passed.
- Live `python -m busfactor.refresh --no-pull --no-github` output:

```text
Refresh summary
  New commits: 0 (none)
  New PRs: 0 (none)
  Became Active: none
  Became inactive: none
  Component risk changes: none
```

## Query explanations

- `15_refresh_watermarks` reads the newest Commit timestamp and PR update timestamp for incremental refresh. Optional matches preserve a result even when the graph is empty.
- `15a_refresh_head_files` updates every known File’s `exists` value from the current HEAD path list. This also detects deletions when no commits are new.
- `15z_refresh_component_risk` counts distinct active, non-bot experts for each Component and classifies its risk. Refresh compares snapshots before and after derivation.
- `15_team_write_observation` stores a shared observation linked to an Agent and stable entity key. Its deterministic ID makes watcher retries idempotent.
- `15b_team_recall` returns observations for question entities plus the newest five team observations. Python resolves entity keys and joins memory to the separate Delta graph.
- `15c_team_record_refresh` stores each refresh summary and links its observations. Refresh records and observations live in `mem_team`.
- `15d_team_list` returns recent observations and refresh runs for the API. It collects each list independently to avoid multiplying rows.

## Reviewer decisions

The PR scan sorts by `UPDATED_AT` and stops at the first PR at or before the graph’s newest PR update timestamp; each refresh page uses a timestamped cache key. New commit authors use the existing cached identity map and the project’s `email:<address>` fallback when no mapping is available.

Watcher notes and user corrections are written only to `mem_team`; corrections retain their source and are labeled as user-provided claims. No commit was created.