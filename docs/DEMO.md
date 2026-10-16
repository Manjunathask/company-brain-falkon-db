# Three-minute demo script

Recorded walkthrough for the public `delta-io/delta` snapshot. Evidence counts are produced by the graph and should be read from the live screen; they are not frozen in this script. The repo snapshot was exported on **2026-10-16**. Record the final video against the submission checkout and mention any newer export date shown in `data/snapshot/manifest.json`.

## Before recording

1. Start the app with `docker compose up --build` and wait for the green graph status in the top-right. The Docker image does not include the local Delta clone, so the refresh step below requires the local development setup.
2. For the chat turn, set `ANTHROPIC_API_KEY` in the host environment and restart Compose. The departure simulator and direct tools need no key.
3. In the browser, open `http://127.0.0.1:8000`. Keep the graph canvas visible beside the controls.
4. In a terminal at the repo root, with `.venv` configured and a local Delta clone present, keep this ready for the refresh section:
   `.venv/Scripts/python -m busfactor.refresh --no-pull --no-github`

## Walkthrough (about 3 minutes)

**0:00–0:20 — Set the question.** Point to the green graph status and say that the browser is asking FalkorDB traversals, not searching a document index. Click **Departure simulator**.

**0:20–0:55 — scottsand-db leaves.** In **Find a person**, enter `scottsand-db`, click **Find**, then click the result labeled `@scottsand-db`. Show the cards for the largest collaboration group before and after, people cut off, and exposed Components. Expand one exposed Component and point to the likely successor evidence. Point at the small answer graph and note that it uses current files and excludes broad bulk commits.

**0:55–1:25 — murali-db leaves.** Replace the search text with `murali-db`, click **Find**, and select `@murali-db`. Compare the exposed Components and successor shown by the live result. The numbers are deliberately read from the panel during recording because they depend on the current snapshot and derive window.

**1:25–1:55 — Ask one traced question.** Click **Ask the graph**. Leave the user login as `murali-db` and ask: **“Why does the IcebergCompat metadata validator in Delta Kernel work the way it does? Trace it to a decision.”** Submit once. Expand **How I know** and point to `decision_trace`, its confidence and evidence path, and the Cypher file. If the paths are title-keyword links, say they are candidates, not confirmed design rationale; the graph does not invent a reason.

**1:55–2:15 — Direct decision trace.** In **Run a graph tool directly**, choose **Decision trace** and enter:

```text
kernel/kernel-api/src/main/java/io/delta/kernel/internal/icebergcompat/IcebergCompatMetadataValidatorAndUpdater.java
```

Click **Run**. Show the returned PR, decision, confidence and the rendered path. Explain that this is graph evidence; a low-confidence title match does not establish causation.

**2:15–2:35 — Refresh and team memory.** This step needs local development setup and a local Delta clone; it is not available inside the Docker image. In the terminal, run `.venv/Scripts/python -m busfactor.refresh --no-pull --no-github`. This refreshes without network calls, updates file existence and derived relations, and writes a `RefreshRun` plus any watcher observations to `mem_team`. Return to **Ask the graph** and point to **Team memory**; explain that notes are shared separately from the company graph and retain their source. If this refresh reports no source changes, show the recorded refresh summary rather than claiming a new code change.

**2:35–3:00 — Recall in a second session.** Open a second browser tab at the same URL. The default user remains `murali-db`; the new session should show the earlier question and any graph changes since it was asked in the memory banner when available. Ask a short follow-up about the same Component. Show that per-user episodes are in `mem_murali-db`, while shared watcher notes come from `mem_team`; the graph joins them by `Entity.key`.

## Date and live numbers

The following expected values were read from the live `delta` graph with `busfactor.tools` on **2026-10-16**. The graph can change as refreshes run, so treat these as a recording check, not hard-coded app output.

| Maintainer | Main collaboration group before → after | People cut off | ORPHANED Components | AT RISK Components (top three by their commits) | Orphaned files |
|---|---:|---|---|---|---:|
| `scottsand-db` | 91 → 90 | none | 2: `kernel/kernel-api/metrics`, `kernel/kernel-api/statistics` | 6: `kernel/kernel-api/snapshot` (31; allisonport-db remains), `kernel/kernel-api/commit` (21; allisonport-db), `kernel/kernel-api/catalogManaged` (10; allisonport-db) | 29 files across 7 Component rows |
| `murali-db` | 91 → 87 | chenwang-databricks, dillitz, ni-mi | 5: `spark-unified/sql` (3 commits), `build/(files)` (1), `kernel/kernel-api/exceptions` (1) | 11: `iceberg/serverSidePlanning` (19; nastra remains), `spark/serverSidePlanning` (18; chenwang-databricks), `iceberg/shadedForDelta` (9; nastra) | 43 files across 18 Component rows |

The selected successor component is the exposed row with the most commits, matching the API's selection rule. For `scottsand-db`, that is `kernel/kernel-api/snapshot`: suggested successor **harperjiang**, 2 shared files out of 2 — `kernel/kernel-api/src/main/java/io/delta/kernel/internal/snapshot/LogSegment.java` and `kernel/kernel-api/src/test/scala/io/delta/kernel/internal/snapshot/LogSegmentSuite.scala`. For `murali-db`, it is `iceberg/serverSidePlanning`: suggested successor **ni-mi**, 3 shared files out of 9 — `iceberg/src/main/scala/org/apache/spark/sql/delta/serverSidePlanning/IcebergRESTCatalogPlanningClient.scala`, `iceberg/src/test/scala/org/apache/spark/sql/delta/serverSidePlanning/ServerSidePlanningCredentialsSuite.scala`, and `iceberg/src/main/java/org/apache/spark/sql/delta/serverSidePlanning/FixedGcsAccessTokenProvider.java`.

The decision-share tool returned **Catalog-Managed Tables** for `scottsand-db`: 43 of 88 implementing PRs (48.9%). For `murali-db`, it returned **Enforce Vacuum Protocol Check**: 1 of 3 (33.3%). These are PR opener shares, not decision participation shares. Neither maintainer had an orphaned decision under the default high-confidence threshold on this graph.

For the IcebergCompat file, `decision_trace` returned four rows, all `low` confidence via `title-keyword`:

| PR | Decision | Issue | Commit (short SHA) |
|---:|---|---:|---|
| #5231 — `[Kernel] Add variant as supported v3 type in IcebergCompatV3` | `IcebergCompatV3` (proposed) | #4574 | `86b84c4d` |
| #4595 — `[Kernel] Introduce IcebergCompatV3` | `IcebergCompatV3` (proposed) | #4574 | `7e5b26f5` |
| #4732 — `[Kernel][#2] IcebergCompatV3 - move IcebergCompatCheck to base class` | `IcebergCompatV3` (proposed) | #4574 | `0d1600e5` |
| #4291 — `[Kernel][icebergWriterCompatV1 - PR#2] Introduce IcebergWriterCompatV1MetadataValidatorAndUpdater for metadata validation and updates for table feature icebergWriterCompatV1` | `IcebergWriterCompatV1` (proposed) | #4284 | `a76fcfe2` |

The local refresh command printed exactly:

```text
Refresh summary
  New commits: 0 (none)
  New PRs: 0 (none)
  Became Active: none
  Became inactive: none
  Component risk changes: none
```

That refresh needs the local development setup and `data/delta` clone; it is unavailable inside the Docker image. The snapshot manifest on this run contained 2,240 parsed commits, 3,602 PRs, 19 RFCs, 220 identity mappings, and 4,427 current-head file paths. Those are input counts, not derived graph counts.
