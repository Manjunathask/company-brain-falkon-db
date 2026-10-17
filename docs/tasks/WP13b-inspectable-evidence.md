<review>
Runs after WP13a (same files: web/app.js, api/app.py, 07b), so read its report first and use its risk codes
(`NO OTHER AUTHOR`, `ONE OTHER AUTHOR`, `COVERED`) and reviewer fields.

The README promises "an answer with the graph path behind it", but a judge cannot inspect that path today. Checked on
2026-10-17:
1. "How I know" shows no values. `agent/loop.py` builds the `trail` entry with tool, params, cypher, row_count and ms
   but drops the rows, and web/app.js prints "row values are not included in this API trace". docs/DEMO.md even tells
   the presenter to show "returned rows".
2. The departure focus graph hides the Person -> PR -> Decision path. `_focused_departure_graph` in api/app.py keeps only
   Person, Component and Decision nodes, so a decision floats next to the person with no visible link. The reviewer
   paths that WP13a adds would be dropped the same way.
3. Decision cards cannot be opened at the source, and nothing marks an explicit link apart from a title-keyword guess.
4. The starter question "Why was Managed Commits rejected, and what replaced it?" gets the replacement and "PR #4382"
   but no reason, because the graph holds none. The reason is public: the body of tracking issue #4381
   (Catalog-managed Tables) has a lead-in paragraph that names the Coordinated Commits RFC (the former name of Managed
   Commits, issue #2598) followed by a numbered list of reasons. The ingest does not fetch issue bodies
   (`ISSUE_FIELDS` in ingest/github_api.py has no `body`).
5. `remember_correction` also writes the visitor's claim into shared `mem_team` as kind `user_claim`. That suits
   Track 02, but on a public demo anyone can write there, and the UI does not mark such rows as unverified.
</review>

<task>
Make every answer's evidence inspectable down to the rows and the source documents. Read AGENTS.md, docs/QUERIES.md
and the WP13a report first.

1. Rows in the trace. Add `rows` to each successful `trail` entry, using the same `_compact_rows` limits the model gets
   (keep `row_count` as the true total and add `rows_truncated` when capped). In "How I know", render each call's rows
   with the existing `readableToolResult` table (plain column headers, never raw JSON), then the parameters, then the
   collapsible Cypher. Remove the "row values are not included" text.
2. Paths in the departure graph. In `_focused_departure_graph` keep PR nodes on the paths that explain a card:
   - decisions: Person -OPENED-> PR -IMPLEMENTS-> Decision, at most 3 PRs per decision, explicit (high) links first;
   - reviewers (from WP13a): either the reviewer's REVIEWED -> PR -> (Commit/File collapsed) -> Component path, or one
     collapsed edge `REVIEWED_IN` from reviewer to component with `props.prs` (count) and `props.collapsed = true`.
     A collapsed edge must be labelled as a summary ("reviewed 4 PRs here") and its PR numbers must appear in the
     area card.
   In web/graph.js draw IMPLEMENTS by confidence: solid for high, dashed for low, with a legend entry ("explicit link" /
   "title match"). Keep Commit and File nodes out of the focus graph (they stay in "Show full evidence").
3. Source cards. Add `prs` to 07b rows: up to 5 `{number, title, confidence, via}` for the person's PRs, explicit
   first. On each decision card (Leave view, and the why_not / decision tool tables in Ask) show links that open in a
   new tab: the RFC document `https://github.com/delta-io/delta/blob/master/<path>` (via DOCUMENTED_IN), the tracking
   issue `https://github.com/delta-io/delta/issues/<n>`, and each PR `https://github.com/delta-io/delta/pull/<n>` with
   a chip: "explicit: issue reference", "explicit: RFC document" or "title match (keyword guess)". Return whatever the
   card needs from Cypher (extend 07b or 10b; one query per file; update headers and docs/QUERIES.md).
4. Decision rationale.
   - ingest/github_api.py: add `body` to `ISSUE_FIELDS` and to `parse_issue` rows; `01d_load_issues` sets `i.body`.
     Make sure the snapshot export and snapshot load carry the issue body (rfc_issues is already a snapshot input).
   - New plain function (e.g. `rationale_excerpt(body, patterns, old_issue)` in src/busfactor/ingest/rfcs.py or a small
     module): find the first paragraph of the replacing decision's tracking-issue body that matches one of the old
     decision's patterns from decision_keywords.py (`managed-commits` covers "coordinated commits" and "managed
     commits") or its issue number (`#2598` or `/issues/2598`); return that paragraph plus the list block directly after
     it (numbered or bulleted lines), verbatim, capped at about 900 characters at a sentence end. No LLM.
   - load.py passes `$rationale` and `$rationaleSource` ('issue #4381') to `02b_superseded_by`, which sets
     `s.rationale` and `s.rationaleSource` next to the existing `s.source`. If the cached issue has no body, store null.
   - `10b_why_not` returns `rationale` and `rationaleSource`. The agent prompt: quote the rationale with its source
     when present; if it is null, say the loaded sources hold no rationale text and point to the issue.
   - The network fetch happens outside your sandbox: build and test with a fixture issue body that has the same shape
     (a lead-in paragraph naming the old RFC, then a numbered list). The reviewer will run
     `github_api rfc_issues --refresh`, reload and re-export the snapshot.
5. Mark visitor claims. In `/api/team` and wherever team memory is shown in the UI, label `kind = 'user_claim'` rows
   "Unverified visitor claim" with their date, and show refresh-agent observations as "From repository refresh". In the
   agent prompt, treat user claims as unverified notes to mention, never as repository facts.
</task>

<action_safety>
Edit only src/busfactor/** (agent/loop.py, agent/prompt.py, api/app.py, ingest/github_api.py, ingest/rfcs.py or a new
module, load.py, snapshot.py if needed), queries/** (01d, 02b, 07b, 10b and their _graph files), web/**, tests/** and
docs/QUERIES.md. Do not touch README.md, docs/DEMO.md, docs/BLOG.md, docs/PROGRESS.md, AGENTS.md, CLAUDE.md,
docs/PLAN.md or docs/tasks/. No network, no live LLM calls, no writes to the live `delta` graph (throwaway test graphs
are fine). Do not overwrite anything under data/raw/ or data/snapshot/. Do not run git commit. Never mention
employers or internal projects.
</action_safety>

<verification_loop>
- Tests: a trail entry carries capped rows and the true row_count; the focus graph for a fixture departure contains
  Person -> PR -> Decision with at most 3 PRs per decision and no Commit/File nodes; `rationale_excerpt` on the fixture
  returns the lead-in paragraph plus its list and nothing from other sections, and returns None when nothing matches;
  02b stores null rationale when the body is missing; the snapshot round-trip keeps issue bodies; user_claim rows are
  labelled in the /api/team response or in the UI rendering helper.
- `.venv/Scripts/python -m pytest -q` and the node UI checks.
- Live, read-only: `/api/departure/scottsand-db` focus graph node and edge counts by label/type, and one decision card's
  links.
</verification_loop>

<compact_output_contract>
One line per numbered item; pytest summary; focus-graph counts for scottsand-db and harperjiang; the exact reviewer
steps for item 4 (commands in order); anything you could not verify.
</compact_output_contract>
