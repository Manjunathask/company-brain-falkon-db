<review>
Reviewer (Claude Code) ran the judges' path: `docker compose -p bfjudge up --build -d` on an empty volume. The image
builds (about 5 minutes) but the app crash-loops:
  bootstrap.py line 20: redis.exceptions.ResponseError: Invalid graph operation on empty key
On a brand-new FalkorDB the `delta` key does not exist, so a read query on it fails instead of returning 0.
Note: in your last run you used the system Python; always use `.venv/Scripts/python` (pytest, falkordb and the live
graph at 127.0.0.1 are available there). The dev FalkorDB is stopped while the reviewer tests Docker; if 127.0.0.1:6379
does not answer, skip the live steps and say so.
</review>

<fixes>
1. bootstrap.py: treat a missing graph as empty (check `GRAPH.LIST` / client.list_graphs() before counting), and wait
   for FalkorDB to answer PING (retry up to 60 s with a clear log line) instead of relying on the container restart
   policy. Log each bootstrap step (load, link, derive) with counts. Add a test for "graph key missing -> load runs" and
   "graph exists and non-empty -> load skipped".
2. LICENSE: delete the LICENSE file you created. The public repo already has the developer's MIT LICENSE (copyright
   Manjunathask), which will be merged in. Keep the README "License" section as: MIT, see LICENSE.
3. README:
   - Quick start: say the first `docker compose up --build` takes about 5 minutes (image build) and that bootstrapping
     the snapshot takes about N seconds (measure it with the loader against a throwaway graph if FalkorDB is reachable;
     otherwise leave the bootstrap time out).
   - "Built with AI assistance": also say the plan and graph model in docs/PLAN.md were drafted with Claude (chat) on
     14 Oct, before coding started (design only, as the rules allow), and that the reviewer ran a review gate, live
     integration tests and the model eval in docs/eval.
4. docs/DEMO.md: give the recorder expected values "as of 2026-10-16" from the live graph (run the tools with
   `.venv/Scripts/python -m busfactor.tools ...`): for scottsand-db and murali-db the main group before/after, people
   cut off, ORPHANED and AT RISK component counts with the top 3 names, orphaned file count, the decision they carry
   and its share, and the suggested successor with shared files; the decision_trace rows for the icebergcompat file;
   and what `refresh --no-pull --no-github` prints. Say plainly that the refresh step needs the local development setup
   (it is not available inside the Docker image).
5. Snapshot verification (if FalkorDB is reachable): rebuild into FALKORDB_GRAPH=delta_snapcheck from the snapshot,
   run link_decisions and derive against it, compare node counts per label and relationship counts per type with
   `delta`, report differences, then delete delta_snapcheck.
</fixes>

<verification_loop>
`.venv/Scripts/python -m pytest -q` must pass.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; the snapshot comparison (or why it was skipped); the DEMO numbers you added.
</compact_output_contract>
