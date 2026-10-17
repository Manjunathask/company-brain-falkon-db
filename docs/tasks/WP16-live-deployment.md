# WP16: read-only live deployment (FalkorDB Cloud + Render)

Written 2026-10-17 by Claude Code. Goal: a public URL judges can open, with the graph on FalkorDB Cloud and
the app on a free host, and no Anthropic key on the server. The rules accept full local setup instructions
instead; the organisers' blog post says they prefer a live deployment.

## What "read-only" means here

- **Chat off.** No `ANTHROPIC_API_KEY` on the server. `/api/health` reports `chatEnabled: false`; the
  Leave view, Draft handover and the named starter chips under Ask still work (they need no model).
- **The `delta` graph is never changed by visitors.** The only graph writes are the bootstrap (once, into an
  empty instance), the temporary `whatif_*` copies made by `GRAPH.COPY` and deleted afterwards, and memory.
- **Visitor notes stay private to that visitor.** Today an availability note or saved handover goes into the
  shared `mem_team` graph, and `GET /api/handover` reads every note there. On a public site that would let
  any visitor publish "scottsand-db is unavailable" about a real maintainer to every other visitor. In public
  mode, notes are written and read per visitor, so a judge can still try Mark unavailable and watch the plan
  change, but nobody sees anyone else's notes.

## Measured on 2026-10-17 (throwaway FalkorDB 4.22.0 container on port 6390, since removed)

| Check | Result |
|---|---|
| `GRAPH.MEMORY USAGE delta` on the live graph | 12 MB (server `used_memory` 28 MB) |
| Snapshot bootstrap (load, link, derive) | 11 s; 11,033 nodes, 39,866 relationships |
| Peak memory during bootstrap, current queries | **681 MB**, all of it in the `commits` load step |
| Peak with the fix below | **51 MB**; identical node, relationship and per-type counts |
| Three departure what-ifs (`GRAPH.COPY` + WCC + betweenness) | 1.5 s total, peak **62 MB**, no `whatif_*` graph left |

The cause: in `queries/01_load_commits.cypher` every file row carries the whole commit map `c`, including its
file list. MERGE and DELETE make the query eager, so all rows are held at once; the 1,150-file commit alone
makes about 1.3 million file maps. A container limited to 100 MB would be killed during load.

## Hosting choice

- **FalkorDB Cloud, free tier**: 100 MB of memory, no credit card, username `falkordb` plus a password set
  at creation, no TLS on this tier, **no persistence or backups**, and an instance unused for a day is stopped
  and deleted after 7 days ([free tier](https://docs.falkordb.com/cloud/free-tier),
  [tiers](https://docs.falkordb.com/cloud/tiers/free)). So the app must reload the graph whenever it finds the
  instance empty, and something must keep it in use during judging.
- **Render, free web service**: builds the existing `Dockerfile` straight from the public GitHub repo,
  512 MB RAM, 0.1 CPU, sleeps after 15 minutes without traffic and takes about a minute to wake, 750 free
  instance hours a month (one service running all month uses about 720)
  ([summary](https://temps.sh/blog/render-pricing-2026), [review](https://jwatte.com/blog/render-com-platform-review.md)).
  Render sets `PORT`, which the app already reads.
- **Fallback host** if 0.1 CPU is too slow: a Hugging Face Docker Space (free, more CPU, sleeps after 48 hours
  idle) or Render's $7 instance. Decide after measuring.

## Code changes (Codex)

Keep each change small and readable; no new framework.

1. **Lean commit load.** In `queries/01_load_commits.cypher` stop carrying `c` after the file unwind:
   `WITH k, c` becomes `WITH k, c.files AS files` + `UNWIND files AS f`, and both `WITH k, c, f, fl` become
   `WITH k, f, fl`. Update the header comment to say why. Re-run `load all --from-snapshot`, `link_decisions`
   and `derive` against a throwaway graph and confirm the counts in the table above.
2. **Cloud connection settings.** `src/busfactor/db.py` reads `FALKORDB_USERNAME` (default none) and
   `FALKORDB_SSL` (`1` turns on `ssl=True`; default off) next to the existing host, port and password.
   Add them to `.env.example` and pass them through in `docker-compose.yml`.
3. **Public mode** behind `BUSFACTOR_PUBLIC=1` (off by default, so local behaviour is unchanged):
   - availability notes and saved handovers require a valid visitor id and are written with that visitor's
     agent (`chat:<visitor>`, as `_team_writer` already does);
   - `GET /api/handover/{login}` takes `visitor`, the web client sends it, and the team-memory reads it
     triggers (`16f_team_availability`, `16h_team_last_handover`, and anything else `handover.py` reads)
     return only that visitor's notes plus non-visitor writers such as the refresh watcher; add a parameter
     to those `.cypher` files rather than filtering in Python, and say so in their headers;
   - `/api/team` shows only non-visitor notes;
   - the page shows one line under the header: "Live demo: chat is off and notes you leave are visible only
     to you."
4. **Self-healing graph.** The free instance has no persistence, so a restart empties it while the app keeps
   running. Before serving `/api/health`, `/api/summary` and the departure and handover endpoints, check (at
   most once a minute, under a lock) that the `delta` graph exists and is not empty; if it is missing, run
   the same snapshot bootstrap as `busfactor.bootstrap` and log it. Never bootstrap over a non-empty graph.
5. **Graceful what-if.** If `GRAPH.COPY` or an `algo.*` call is refused by the managed server, the departure
   view still returns the author and review results with a note that the collaboration what-if is
   unavailable, instead of a 500.
6. **Keep-alive.** `.github/workflows/keepalive.yml`: every 10 minutes, `curl -fsS` the live
   `/api/health` (URL from a repository variable `LIVE_URL`; skip when unset). This keeps Render awake and
   the FalkorDB instance in use. Also allow manual runs.
7. **`render.yaml`** (Render Blueprint): one Docker web service, health check `/api/health`, env vars
   `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_USERNAME`, `FALKORDB_PASSWORD` (all `sync: false`, entered by
   the developer in the dashboard), `FALKORDB_GRAPH=delta`, `BUSFACTOR_INPUT=snapshot`, `BUSFACTOR_PUBLIC=1`,
   `HOST=0.0.0.0`. No Anthropic variables.
8. Tests: lean-load counts (integration, skipped without FalkorDB), username/SSL settings, public-mode note
   scoping (two visitors, each sees only their own note), bootstrap-on-empty, and what-if degradation.

README, DEMO and PROGRESS edits stay with Claude Code.

## Steps for the developer (accounts and secrets)

1. **FalkorDB Cloud** (https://app.falkordb.cloud): sign up, create a **Free** instance on AWS in a region
   close to the Render region you will pick (for example AWS `us-east-1` with Render Virginia, or an EU
   region with Render Frankfurt). Set the password at creation. Note the host and port.
2. Store the connection details as Machine-scope environment variables on this PC, the same way as
   `GITHUB_TOKEN`, so Claude Code can verify the instance without seeing the password:
   `FALKORDB_CLOUD_HOST`, `FALKORDB_CLOUD_PORT`, `FALKORDB_CLOUD_PASSWORD` (username is `falkordb` unless you
   changed it).
3. **Render** (https://render.com): sign up with GitHub and allow it to read
   `Manjunathask/company-brain-falkon-db`. After the WP16 commit is pushed, create the service from
   `render.yaml` (New, Blueprint) and type the four FalkorDB values into the dashboard yourself.
4. **GitHub**: add a repository variable `LIVE_URL` with the Render URL, so the keep-alive workflow runs.
   If pushing the workflow file is refused (it needs the `workflow` token scope), use a free UptimeRobot
   monitor on `/api/health` every 5 minutes instead.

## Deploy and verify (Claude Code)

1. Against the Cloud instance from this PC: check the server version, that `GRAPH.COPY`, `algo.WCC` and
   `algo.betweenness` are allowed, run the snapshot bootstrap, and compare counts with the table above;
   record peak memory with `INFO memory` if the server allows it.
2. After Render deploys: `/api/health` (`chatEnabled: false`, 11,033 nodes), headline **25 of 69**,
   `harperjiang` departure (3 / 5 / 80 / 0), handover `flink/inttest` → scottsand-db, and the timing of each.
3. Visitor scoping in two separate browser profiles: mark scottsand-db unavailable in one; the other still
   sees scottsand-db suggested.
4. Delete the `delta` graph on the Cloud instance once and confirm the app rebuilds it.
5. README gets a **Live demo** section (URL, chat off, notes private, may take a minute to wake); DEMO notes
   that the video uses a local run with chat on; PROGRESS gets the measurements.

## Done when

The public URL serves the Leave view and handover packets from FalkorDB Cloud, two visitors cannot see each
other's notes, an emptied instance rebuilds itself, the keep-alive is running, and README links the URL.
