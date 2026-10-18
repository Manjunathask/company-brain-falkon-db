# Fact check

Every number and factual claim in `ARTICLE.md`, where it came from, and how it was verified on **18 Oct 2026**.

**How verified.** *Live*: recomputed read-only against the running `delta` graph. *Code*: read in the repository.
*Doc*: project docs or task reports. *Measured*: timed or measured on this machine. The read-only recomputation
script is kept in the session scratchpad; its key outputs are quoted below.

## Headline numbers and the correction

| Claim in the article | Value | Source | How verified |
|---|---|---|---|
| Active code areas with bus factor 1, last 12 months (corrected) | 25 of 69 | `queries/05b_bus_factor_component.cypher` (minCommits 2, minTotal 5, test resources excluded) | Live |
| Old headline | 42 of 87 | the pre-WP13a query (`git show fa6413c^:queries/05b_bus_factor_component.cypher`), re-run on the same graph | Live: still returns 42 of 87 today |
| Other windows (not in article; README cites them) | 6 months: **19 of 48** (README says 18 of 48 on 17 Oct); 24 months: 39 of 101 | same query, other `$since` | Live; the 6-month value moved with the window |
| Old query mixed windows: kept people by latest commit, summed two-year `KNOWS.commits` | — | old query text; WP13a brief finding 1 | Code + Doc |
| Leaving person needed only 1 commit in the old departure query | — | `git show fa6413c^:queries/06_departure_impact.cypher` (no `$minCommits` on the leaving side) | Code |
| murali-db: five "orphaned" areas, four on a single commit | spark-unified/sql 3; build/(files), kernel/kernel-api/exceptions, spark-unified/spark-4.0-4.1, spark/metering 1 each | old 06 query re-run | Live |
| Top 15 active people: 19 areas where they're the only recent author, each with 2–11 active reviewers | 19; range 2–11 | `06_departure_impact` for the top 15 by in-window commits | Live |
| `count(DISTINCT commit)`; bulk commits (>100 files) and deleted files excluded | 100-file cutoff | `03d_mark_bulk_commits.cypher`, `derive.py` `DEFAULT_MAX_COMMIT_FILES = 100`, `05b` WHERE clause | Code |
| Review commissioned from Codex on GPT-6-Astra, checked by Claude Code | 17 Oct | your message in the 17 Oct session; `docs/tasks/WP13a-honest-measurements.md` | Doc + session record |
| The 42/87 headline appeared on the landing page with the WP11 redesign and was corrected the same day | 17 Oct | `docs/PROGRESS.md`, commits `d0b7d03`, `fa6413c` | Doc |

## Graph and data

| Claim | Value | Source | How verified |
|---|---|---|---|
| Commits, PRs, RFCs, head files | 2,240 · 3,602 · 19 · 4,427 | `data/snapshot/manifest.json` | Doc |
| Graph size | 11,033 nodes · 39,869 relationships | `00_counts` | Live. A fresh snapshot rebuild gives 39,863 (REVIEWED 4,626 vs 4,627 and WORKS_WITH 877 vs 882, both noted in PROGRESS) |
| Snapshot size | 1.7 MB (1,742,170 bytes across 8 files) | `data/snapshot/` | Measured |
| Rebuild time | about 11 s | bootstrap into a throwaway FalkorDB 4.22.0 container | Measured (10.6 s; machine-dependent) |
| Graph memory | 12 MB | `GRAPH.MEMORY USAGE delta` | Live |
| Load peak 681 MB → 51 MB after the `01_load_commits` fix, identical counts | 681 / 51 MB | throwaway container, old vs new query on the same day | Measured; fix committed as `24409e1` |
| Decision links | 283 total: 230 title-keyword (low), 26 issue-ref + 27 rfc-doc (high) = 53 explicit | `IMPLEMENTS.via/confidence` | Live |
| Keywords match on word boundaries ("ICT" vs "conflict") | `\bICT\b` | `src/busfactor/decision_keywords.py` | Code |
| Managed Commits = Coordinated Commits | tracking issue #2598, "Delta Coordinated Commits" | Decision → TRACKED_IN → Issue | Live |
| Managed Commits → Catalog-Managed Tables, source PR #4382, reason from issue #4381 | — | `SUPERSEDED_BY {source, rationaleSource}` | Live |

## Worked example (Hao Jiang, flink/inttest)

Nothing in the data suggests Hao Jiang is leaving; the article says so explicitly.

| Claim | Value | Source | How verified |
|---|---|---|---|
| Hao Jiang is the only person with 2+ commits in `flink/inttest` in 12 months | theirCommits 3, remaining [] | `06_departure_impact` | Live |
| Departure sentence: 3 / 5 / 81 / 0 | 3 no other author, 5 one other author, 81 files, 0 cut off | app `/api/departure/harperjiang`; screenshot | Live. **Note:** DEMO.md says 80 files (17 Oct); the window moved |
| The three Flink areas have 5–6 active reviewers | 5, 5, 6 | `06_departure_impact.reviewerCount` | Live |
| Path: harperjiang → commit fa642d6 → CatalogManagedTableIntTest.java → flink/inttest; commit → PR #6188 ← scottsand-db | — | read-only path query | Live |
| PR #6188 reviewers; title-keyword link to Catalog-Managed Tables | huan233usc, tdas, scottsand-db; via title-keyword, low | PR node | Live |
| Handover candidates and their columns (scottsand-db 2 of 3 PRs, 0 files, 0 own commits; kaiqijinwow 1 of 3, 1 of 9, 1 commit; …) | — | `18_handover_candidates` via `/api/handover` | Live + screenshot |
| Reading list #6188 (7 files), #6192 (3), #6933 (1) | — | `18b_handover_reading` | Live + screenshot |
| "took part in Catalog-Managed Tables" | high-confidence `PARTICIPATED_IN` | `04b`/`04c` derive queries | Code + Live |
| Ordering is a plain sort, not a weighted score | `ORDER BY skipped, reviewedTheirPRs DESC, sharedFiles DESC, areaCommits DESC, areaReviews DESC, login` | `18_handover_candidates.cypher` | Code |
| The suggestion sentence is built in Python from the row | `why_sentence()` | `src/busfactor/handover.py` | Code |
| Packet in about a tenth of a second | 0.087–0.144 s over HTTP (3 calls) | `/api/handover/harperjiang?component=flink/inttest` | Measured |
| Departure view in about a second | 0.82–0.98 s over HTTP (3 calls, includes the what-if) | `/api/departure/harperjiang` | Measured |
| What-if: harperjiang cuts off 0 (main group 91→90); murali-db cuts off 3 and ranks 1st by betweenness | — | `simulate_departure` (`whatif.py`, queries 09, 09c, 09d) | Live |
| What-if method: copy, rank by betweenness, remove Active, recompute WCC over WORKS_WITH, compare, delete | — | `src/busfactor/whatif.py` | Code |

## Memory

| Claim | Source | How verified |
|---|---|---|
| Separate graphs: `mem_team` (shared), `mem_v_<visitor>` (per browser) | `team_memory.py`, `agent/memory.py`, `GRAPH.LIST` | Code + Live |
| Cypher can't cross graphs; the join is by `Entity.key` in Python | `agent/memory.py` docstring; AGENTS.md | Code + Doc |
| The note is passed to the handover query as `$exclude` | `handover.py` `build_packet` | Code |
| "What changed" text and "Unverified availability note" label | app output, screenshot s5 | Live |
| The availability note ("on leave until January") was invented for the demo | typed by the article's capture script into a throwaway graph | Process (stated in the article and figure 6) |
| The chat agent made 1 tool call (`handover_plan`) and named the note unverified | Ask view, screenshots s6/s7 | Live (two runs of the same question, ~10 s each) |

## Architecture and agent

| Claim | Source | How verified |
|---|---|---|
| No Cypher generated at runtime; each tool is one `.cypher` file | `tools.py` registry, `queries/` | Code |
| Read-only tools run through `GRAPH.RO_QUERY` | `tools.py` (`ro_query`) | Code |
| Agent can only name catalogue tools with known parameters | `agent/loop.py` `_validate` | Code |
| Names are checked before a tool runs (`harper-jiang` → not in the graph) | `tools.run_tool` / `resolve_inputs` (WP15, `25a2a01`) | Live |
| Names in the reply are compared with the rows | `agent/reply_check.py` | Code + screenshot s7 |
| Agent model Claude Sonnet 5.5; evaluation: 69 s and $0.37 vs 112 s and $1.17 for Opus 5.5 | `docs/eval/`, README | Doc (not re-run) |
| Three live-only breakages (FalkorDB error wording, Windows `localhost` delay, 24-optional-parameter limit) | `docs/PROGRESS.md`, `docs/tasks/WP7c-tool-schema-fix.md`, WP3 reviews | Doc |

## Your contributions and AI assistance

Taken from your own messages in the Claude Code session records for this project: kickoff and delegation (15 Oct),
the Sonnet-over-Opus choice (16 Oct), newcomer UI feedback (16 Oct), screenshot feedback (17 Oct), the GPT-6-Astra
review and the Must/Should choice (17 Oct). These match the README's "Built with AI assistance" section.

## Unresolved or flagged

1. **Planning before the hackathon.** "I planned the project with Claude" comes from `docs/PLAN.md` (dated 14 Oct) and
   the README. That chat happened on claude.ai and isn't in the session records. Please confirm the wording.
2. **The flagged name in screenshot s7.** The reply check reported "1 name not found in the results" in that run. The
   app doesn't show which name in the cropped area, so the article only says that one name was flagged.
3. **Numbers that move daily.** Counts tied to the 12-month window (81 files; 6-month 19 of 48) shift as days pass.
   The article dates its figures to 18 Oct 2026.
4. **App issue seen, not used.** The Ask view's evidence graph for "Why was Managed Commits rejected…" drew its 41
   nodes in a single horizontal line. That screenshot is not in the article. It may be worth a look before recording
   the demo.
