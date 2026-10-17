# Three-minute demo script

This walkthrough follows the current UI against the live `delta` graph. Values were read from the local API on
**2026-10-17**; they move a little as the 12-month window advances or after a refresh, so check the table at the end
before recording.

The story: one maintainer leaves, the graph shows what is exposed and what that claim rests on, and the app turns the
finding into a handover plan that changes when the team learns something new.

## Before recording

- Start the app with an Anthropic API key on the server (`/api/health` shows `"chatEnabled": true`).
- Use a fresh browser profile, about **1280 × 765** or larger, so the evidence graph sits beside the results.
- Rehearse in that profile, then click **Start over** under the Ask composer. It deletes this browser's history and the
  notes and saved handovers it wrote to team memory, so the recording starts clean (otherwise the first packet already
  shows a skipped candidate or a "What changed" line).
- The agent answer in step 5 takes about 30 seconds; trim the wait in editing.

## Walkthrough (about 3 minutes)

**1. The number (0:00–0:20).** The page opens on **What if someone leaves?** with the heading **25 of 69 active code
areas in Delta Lake have a bus factor of 1**. Open **What is a bus factor?**: one person wrote at least half of an
area's qualifying commits in the last 12 months. Say what it is not: it measures who wrote the code, not who
understands it.

**2. One maintainer leaves (0:20–0:55).** Click **Search by name or GitHub login**; the list is the top 10 by recent
commits. Choose **Hao Jiang (@harperjiang)**. Read the sentence: "If Hao Jiang left: 3 code areas where they made 2+
commits in the last 12 months would have no other recent author (3 of them were reviewed by other active people), 5
would have one other recent author, 80 current files would have no other recent editor, and 0 people would lose their
link to the main collaboration network." Open **No other recent author · 3**: `flink/kernel`, `flink/inttest` and
`flink/(files)`. Each card says **Reviewed by:** with PR counts, for example `flink/inttest`: scottsand-db (2 PRs),
timothyw553 (2 PRs), huan233usc (1 PR), 5 active reviewers. In **Departure evidence**, point to the dotted
"reviewed 2 PRs here" edges. The line to say: *authorship says nobody else is left in these Flink areas; the review
graph says five people have seen the code.*

**3. Draft the handover (0:55–1:45).** On the `flink/inttest` card click **Draft handover**. Walk down the packet:
- **Suggested successor: scottsand-db**: "Reviewed 2 of Hao Jiang's 3 PRs here; no commits of their own here yet; took
  part in Catalog-Managed Tables." The table keeps each kind of evidence in its own column; the order is a plain sort,
  reviews of this person's PRs first. **Not touched by scottsand-db yet** lists the files only Hao Jiang edited.
- **Read these first**: #6188 "[Flink] Support Catalog-Managed Table with UC" (7 files here, chip "Catalog-Managed
  Tables · title match"), #6192, #6933, each a GitHub link.
- **Decisions to preserve**: Catalog-Managed Tables, "0 explicitly linked PRs here · 1 title matches (keyword
  guesses) · replaces Managed Commits", with RFC and issue links and the stated reason **quoted from issue #4381**.
- **Questions for Hao Jiang**: two files only they edited, "Was PR #6188 part of Catalog-Managed Tables?
  (title-keyword guess)", and two walk-throughs for scottsand-db.
Click **Save to team memory** ("Saved to team memory…"). Mention **Copy as Markdown**: the packet pastes into a
GitHub issue as a checklist.

**4. Memory changes the plan (1:45–2:10).** In the candidate table click **Mark unavailable** next to scottsand-db,
type `on leave until January`, press **Save note**. The packet redraws: **What changed: The packet saved on 17 Oct
2026 suggested scottsand-db; now kaiqijinwow. Why: scottsand-db was marked unavailable on 17 Oct 2026: on leave until
January (unverified note).** The new successor line reads "Reviewed 1 of Hao Jiang's 3 PRs here; edited 1 of the 9
files Hao Jiang changed; 1 commit of their own here." Point to the **Skipped** line and its "Unverified availability
note" label: team claims never become repository facts.

**5. Another agent sees the same memory (2:10–2:40).** Click **Ask**, type `Draft a handover plan for flink/inttest if
harperjiang leaves.` and press **Enter**. The agent calls `handover_plan`, suggests kaiqijinwow and says scottsand-db
was skipped because of the unverified note. Expand **How I know**: the tool's result rows as a table, its parameters,
and **Cypher query**. This is Track 02: the page and the chat agent share state through the `mem_team` graph.

**6. How it works (2:40–3:00).** Every number came from a `.cypher` file: `05b` for the headline, `06` for the
departure (authors and reviewers counted separately), `18_handover_candidates`, `18b`, `18c` for the packet, plus
`algo.betweenness`, `algo.WCC` and `GRAPH.COPY` for the collaboration what-if. Memory lives in separate graphs
(`mem_v_<id>` per visitor, `mem_team` shared), joined to `delta` by `Entity.key` in Python.

## Optional extras

- **A decision's reason:** on Ask, click the chip **Why was Managed Commits rejected, and what replaced it?** The
  answer quotes the three reasons from issue #4381 and **How I know** shows them in the "Stated reason (quoted)" column.
- **Keyword guesses kept apart:** choose **Scott Sandre (@scottsand-db)**; the decision card reads "Explicitly linked
  PRs: they opened 1 of 3 · Title match only: 42 of 85", with each PR marked explicit or title match.
- **Full evidence:** under the departure results, **Show full evidence** draws the PRs, commits and files behind the
  summary edges; **Show focused evidence** returns to the readable view.
- **Refresh (local development only):** `.venv/Scripts/python -m busfactor.refresh` pulls new commits and PRs and
  writes refresh observations; the landing page then shows a **Last refresh** line in recent-author terms.

## No API key

**What if someone leaves?** and **Draft handover** (including saving and availability notes) work without a key. On
**Ask**, the named starter chips call their graph tools directly and show readable tables; free-form questions explain
that chat needs an Anthropic API key on the server.

## Expected values as of 2026-10-17

| Check | Expected value |
|---|---|
| Landing headline | **25 of 69** areas with bus factor 1 (18 of 48 over 6 months, 39 of 101 over 24 months) |
| `harperjiang` (Hao Jiang) | **3** no other recent author (flink/kernel 5 reviewers, flink/inttest 5, flink/(files) 6), **5** one other recent author, **80** current files, **0** cut off; departure graph 20 nodes |
| Handover `harperjiang` · `flink/inttest` | successor **scottsand-db** (2 of 3 PRs reviewed); reading list #6188, #6192, #6933; decision Catalog-Managed Tables (title match, reason from issue #4381); 5 questions |
| After marking scottsand-db unavailable | successor **kaiqijinwow** (1 of 3 PRs reviewed, 1 of 9 files, 1 commit) with a "What changed" line |
| `scottsand-db` | 2 no other recent author, 2 one other recent author; Catalog-Managed Tables explicit **1 of 3**, title match **42 of 85** |
| `murali-db` | 1 no other recent author (spark-unified/sql, 7 reviewers), 6 one other recent author, 43 files, 3 cut off |

Timing on 2026-10-17: departure view 0.5–0.75 s, handover packet under 0.1 s, agent answers about 30 s (two model
rounds; the graph tools take under 0.1 s of that).
