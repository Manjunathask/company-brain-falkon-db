# WP13b report

Built by Claude Code (the developer asked for it directly while Codex was out of usage), verified live on 2026-10-17.

1. Rows in the trace: each successful `tool_calls` entry carries `rows` (the same `_compact_rows` the model sees),
   the true `row_count`, and `rows_truncated` when capped. "How I know" renders them with the shared `toolTable`
   (plain headers, capped lists as "a, b (+N more)", no raw JSON), then parameters, then the Cypher.
2. Departure focus graph: Person -OPENED-> PR -IMPLEMENTS-> Decision for at most 3 of the person's PRs per decision,
   explicit first (taken from 07b's `prs`); IMPLEMENTS is solid for explicit and dashed for title match. Reviewers of
   NO OTHER AUTHOR areas get one collapsed `REVIEWED_IN` edge each (top 3, labelled "reviewed 4 PRs here", dotted);
   the PRs behind it stay in "Show full evidence". People left without a link are dropped. Legend extended.
   Node counts: murali-db 17, scottsand-db 14, harperjiang 20.
3. Source cards: 07b returns `prs` ({number, title, confidence, via}, explicit first), `slug`, `issue`, `rfcPath`.
   Decision cards link the RFC document, the tracking issue and each PR with "explicit: issue reference",
   "explicit: RFC document" or "title match (keyword guess)". The why_not table links the discussion issue.
   Area cards list reviewers with PR counts (06 `reviewerPRs`).
4. Rationale: `body` added to the issue GraphQL fields, `parse_issue` and `01d`; `rationale_excerpt` (ingest/rfcs.py)
   takes the first paragraph naming the old RFC (keyword patterns or issue #2598) plus the list after it, verbatim;
   `02b` now takes `$old/$new/$source/$rationale/$rationaleSource` from load.py; `10b` returns `rationale` and
   `rationaleSource`. Reviewer steps run: `github_api rfc_issues --refresh` (19 issues, only bodies changed),
   `load issues`, `load decisions`, `snapshot export` (only rfc_issues.json.gz and the manifest changed), and a
   throwaway-graph load from the snapshot (rationale 1,015 characters from issue #4381; graph deleted).
5. Visitor claims: `/api/team` observations carry `label` ("Unverified visitor claim" / "From repository refresh");
   the agent's teamClaims carry the same label and the prompt treats them as unverified notes.

pytest: 109 passed; node tests/js passed; `scripts/smoke_live.py` passed (20 s). Live agent answer to "Why was Managed
Commits rejected, and what replaced it?" quotes the three reasons from issue #4381 (about 36 s, three model rounds).
