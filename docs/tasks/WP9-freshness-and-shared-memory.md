<task>
You are implementing work package WP9 of "Bus Factor" (Graph Hacks, FalkorDB), Track 02 "Agent Memory and
Coordination". Read AGENTS.md, docs/PLAN.md (Freshness and Memory), docs/PROGRESS.md, docs/QUERIES.md and README.md.
Everything before is committed. FalkorDB is reachable at 127.0.0.1. Your sandbox has no network: the reviewer runs
`git pull` and the GitHub fetch; you write and test the code with fixtures.

Goal: the graph stays current, and agents remember and share what changed.

Build:
1. Incremental refresh, src/busfactor/refresh.py, `python -m busfactor.refresh [--no-pull] [--no-github]`:
   - optionally `git -C <DELTA_REPO> pull --ff-only` (skip with --no-pull);
   - parse only commits newer than the newest Commit.ts already in the graph (reuse git_log parsing; read the
     watermark with a query file); recompute File.exists from HEAD;
   - fetch only PRs created or updated since the newest PR in the graph (refresh just the first pages of the GitHub
     PR listing until a known, unchanged PR is reached; never re-download everything; keep caching raw responses
     under data/raw/github/ with a timestamped key so old pages stay intact);
   - load the new rows with the existing idempotent load queries, then link_decisions and derive;
   - write a RefreshRun record (see 3) and print a short "what changed" summary: new commits per component, new PRs,
     people who became Active or inactive, components whose risk changed (ORPHANED / AT RISK / COVERED) compared with
     before the refresh. Compute the before/after risk with the existing 06-style queries per component.
2. "Since you last asked". In memory recall (agent/memory.py), for every Entity the user asked about before, call
   14d_changed_since with the last-asked timestamp and put the result in the first user message, e.g.
   "Since you last asked about component:kernel/kernel-api/commit (2026-10-16 18:02): 3 new commits by allisonport-db".
   The UI already shows recall at the top of a session; make sure the API returns it in a field the UI reads.
3. Shared team memory between agents (coordination). A second graph `mem_team`:
   (:Agent {name}) -[:WROTE]-> (:Observation {text, ts, kind, source}) -[:ABOUT]-> (:Entity {key})
   (:RefreshRun {ts, newCommits, newPRs}) -[:OBSERVED]-> (:Observation)
   - The watcher agent is the refresh job: after each refresh it writes one Observation per material change (risk
     changed, new decision activity, a person went inactive) with Agent {name:'watcher'}. Deterministic, no LLM.
   - The chat agent (agent/loop.py) reads mem_team Observations about the entities in a question (and the newest 5
     overall) before answering, and its remember_correction tool now also writes the correction to mem_team as an
     Observation by Agent {name:'chat:<user>'} with source = the user, so other users' sessions see it (marked as a
     user-provided claim, never a graph fact).
   - Query files 15_team_write_observation, 15b_team_recall, 15c_team_record_refresh (headers as usual). Cypher cannot
     cross graphs; join by Entity.key in Python as memory.py already does.
4. API/UI: GET /api/team returns recent Observations and RefreshRuns; the UI shows a small "Team memory" list
   (watcher and chat observations, with agent name and time) in the Ask tab. POST /api/refresh is NOT exposed (the
   refresh runs from the CLI only).
5. Tests: refresh with fixture git output and fixture GitHub pages (watermark respected, nothing re-loaded, risk diff
   computed, Observations written); recall shows changed-since; a correction written by user A is visible in user B's
   recall as a user-provided claim; mem_team integration test on throwaway graphs.
6. docs/QUERIES.md entries for the new queries; README "Memory (Track 02)" section rewritten in a few sentences to cover
   per-user memory, shared team memory, the watcher agent and refresh. Append to docs/PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/ or data/delta (read-only git
commands are fine). Do not run git commit. No network, no live LLM calls. Never write corrections or observations
into the `delta` graph.
</action_safety>

<verification_loop>
pytest must pass. Run `python -m busfactor.refresh --no-pull --no-github` against the live graph (nothing new should
load; the summary should say so) and show its output.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; the refresh output; decisions for the reviewer; anything uncertain.
</compact_output_contract>
