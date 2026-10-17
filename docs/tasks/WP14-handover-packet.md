<context>
Runs after WP13a and WP13b. Read both reports, AGENTS.md, docs/QUERIES.md and the hackathon track text below.

Track 03 (Company Brain, our main track) asks for "the best agent that understands how a company works and gets work
done". Today Bus Factor diagnoses a departure but stops there. This package makes it produce the thing a team needs
next: a sourced handover plan for one exposed area. Track 02 asks for agents that "remember across sessions and share
state", including "shared state and handoffs between agents". The packet is also the Track 02 demo: it is saved to the
shared `mem_team` graph, and a sourced availability note left by another agent or visitor changes the next packet.

Demo shape (one area, about 60 seconds of video): pick the leaving person and an area marked NO OTHER AUTHOR
(WP13a: e.g. harperjiang and flink/kernel; the final pair comes from your report) -> "Draft handover" -> the packet
names a candidate and says why -> save it -> in Ask, tell the agent that candidate is unavailable -> redraft: the
candidate is skipped, with the note and its source shown, and the packet says what changed.

Positioning: ownership-risk tools already exist (CodeScene sells knowledge-distribution and offboarding simulation).
Our difference is decisions plus review evidence plus a handover you can act on, every item linked to its source.
</context>

<task>
1. Candidate query `queries/18_handover_candidates.cypher`. Params: `$login`, `$component`, `$since`, `$exclude`
   (logins to skip), `$limit` (default 5). Candidates are Active, non-bot people other than `$login`, not in `$exclude`,
   who in the window either authored a non-bulk commit touching a current file in the component, or reviewed
   (`review.at > $since`) a PR that has such a commit. Return separate evidence columns, each aggregated in its own WITH
   stage with `count(DISTINCT ...)` so they cannot multiply:
   - `reviewedTheirPRs`: PRs with `$login`'s in-window commits in this component that the candidate reviewed;
   - `sharedFiles`, `outOf`: current files `$login` edited here in the window that the candidate also edited;
   - `areaCommits`: the candidate's in-window commits here;
   - `areaReviews`: in-window PRs touching this component that the candidate reviewed;
   - `sharedDecisions`: titles of decisions linked to this component (as in item 3) where the candidate has a
     high-confidence PARTICIPATED_IN;
   - `toLearn`: up to 5 current files in this component that only `$login` edited in the window and the candidate has
     never authored.
   Order by `reviewedTheirPRs DESC, sharedFiles DESC, areaCommits DESC, areaReviews DESC, login`, a plain order with no
   weights, so it can be explained in one sentence. Say in the header why reviews of this person's PRs rank first
   (the candidate has already seen these changes).
2. Reading list `queries/18b_handover_reading.cypher`. Params: `$login`, `$component`, `$since`, `$limit` (3). PRs that
   contain `$login`'s in-window, non-bulk commits touching current files in the component. Rank: has a high-confidence
   IMPLEMENTS link first, then distinct component files touched, then most recent `mergedAt`. Return number, title,
   mergedAt, `filesHere`, `decisions` as `{title, confidence}` maps and `reviewers` (non-bot logins).
3. Decisions to preserve `queries/18c_handover_decisions.cypher`. Params: `$login`, `$component`. Decisions linked to
   the component through Commit -PART_OF-> PR -IMPLEMENTS-> Decision (all loaded history), or through a DOCUMENTED_IN
   file in the component. Return title, slug, status, `explicitPRs`, `titleMatchPRs`, the issue number and RFC path
   for the WP13b source links, the WP13b `rationale`/`rationaleSource` when the decision is either end of a
   SUPERSEDED_BY edge (with the other decision's title), `leavingParticipated` (high-confidence PARTICIPATED_IN by `$login`) and `otherActive`
   (other Active, high-confidence participants). Explicit links first; at most 5.
4. Packet builder `src/busfactor/handover.py`, plain Python over those queries plus `06b_departure_files` for this
   component:
   - `successor`: the top candidate with a "why" sentence built only from the columns, e.g. "Reviewed 6 of Harper's 9
     PRs here, edited 2 of the 12 files Harper changed, no commits of their own here yet."; the full candidate table;
     and `toLearn`.
   - `read`: the 18b rows; `preserve`: the 18c rows.
   - `ask`: up to 6 questions for the leaving person, from templates, each with the row it came from:
     a file only they edited -> "What should the next owner know before changing <path>?";
     a decision they took part in with no other active participant -> "Which constraints from <decision> must be kept?";
     a reading-list PR whose only decision link is a title match -> "Was PR #n part of <decision>? (title-keyword guess)";
     the top candidate's `toLearn` -> "Can you walk <candidate> through <path>?".
   - `skipped`: excluded candidates with the availability note, its date and source (item 5).
   - `changed`: when a packet for this person and component was saved before, the earlier date and candidate, and
     why the candidate differs now (marked unavailable, or new activity: in-window commit and PR counts since that date).
   - `caveat` (always shown): "Suggested from public GitHub activity. Confirm availability, interest and readiness with
     the people involved."
   - `markdown`: the whole packet as a checklist someone can paste into an issue, with GitHub links for every PR,
     issue and RFC, and a footer naming the queries it came from and the date.
   - `graph`: one companion `queries/18_handover_graph.cypher` returning the paths behind the packet: leaving person
     -OPENED-> reading PRs -IMPLEMENTS-> decisions, candidates -REVIEWED-> those PRs, and the component. No Commit or
     File nodes.
5. Shared memory (Track 02). Use the existing `mem_team` graph and Entity.key joins in Python (Cypher cannot cross
   graphs), one query per file:
   - write availability: an Observation of kind `availability` about `person:<login>` with `status`
     ('unavailable' | 'available'), `reason`, `source` (visitor id, or the agent name) and `ts`; the latest observation
     per person wins;
   - read the latest availability for a list of logins; unavailable logins become `$exclude`;
   - save a packet: an Observation of kind `handover` about `component:<name>` with `person`, `candidate`, `ts`,
     `source` and a one-line text;
   - read the latest saved handover for a person and component.
   Availability notes are unverified claims: label them that way everywhere, like WP13b's visitor claims.
6. Agent tools in tools.py / agent/loop.py: `handover_plan(login, component)` (read-only; returns the packet without
   markdown and graph to keep the model context small) and `mark_unavailable(login, reason)` (writes item 5's
   availability observation with source `chat:<visitor>`; special-cased like `remember_correction`). Add both to
   TOOL_LABELS and the system prompt ("when a user says a person is away or unavailable, record it with
   mark_unavailable; when asked about a handover, call handover_plan"). The tool-schema budget test must still pass.
7. API: `GET /api/handover/{login}?component=` (the packet), `POST /api/handover/{login}/save` ({component, visitor}),
   `POST /api/availability` ({login, status, reason, visitor}). 404 for an unknown active person or component.
8. UI (web/**): a "Draft handover" button on every NO OTHER AUTHOR and ONE OTHER AUTHOR area card. It opens a handover
   panel in the left column with: Successor (the why sentence, candidate table with plain headers, "What they have not
   touched yet", a "Mark unavailable" button per candidate that asks for a short reason), Read these first (PR links
   with decision chips), Decisions to preserve (WP13b source cards and rationale), Questions for <name>, Skipped
   candidates with their notes, the "What changed" line when present, the caveat, and "Copy as Markdown" and
   "Save to team memory" buttons. The evidence panel shows the packet graph. Names or "they", never inferred pronouns.
   Readable at 1280 x 765 and on mobile.
</task>

<action_safety>
Edit only queries/** (new 18* and team-memory query files), src/busfactor/** (new handover.py, tools.py, agent/loop.py,
agent/prompt.py, api/app.py, team_memory.py), web/**, tests/** and docs/QUERIES.md. Do not touch README.md,
docs/DEMO.md, docs/BLOG.md, docs/PROGRESS.md, AGENTS.md, CLAUDE.md, docs/PLAN.md or docs/tasks/. Read-only against the
live `delta` graph; writes only to throwaway test graphs (never the live `mem_team`). No live LLM calls (the reviewer
runs scripts/smoke_live.py). Do not run git commit. Never mention employers or internal projects.
If time is short, cut in this order: the "What changed" line, then the packet graph companion. Never cut the caveat,
the source links or the separate evidence columns.
</action_safety>

<verification_loop>
- Fixture tests: candidate columns do not multiply (a candidate with 3 reviews and 2 shared files gets exactly 3 and 2);
  `$exclude` removes a candidate and it appears in `skipped` with its note; the latest availability wins;
  a title-match-only PR yields the "(title-keyword guess)" question; the markdown has a link for every PR, issue and RFC
  in the packet; a saved packet followed by an availability note produces a "changed" entry naming the reason.
- `.venv/Scripts/python -m pytest -q`, node UI checks, and the schema budget test.
- Live, read-only: build packets for the five NO OTHER AUTHOR areas with the most leaving-person commits from the WP13a
  report, and time `/api/handover` (target under 2 s).
</verification_loop>

<compact_output_contract>
One line per numbered item; pytest summary; for each of the five live packets: login, component, top candidate and
why sentence, candidate count, reading-list size, decisions (explicit/title-match), question count, time; your pick of
the demo pair and why; anything you could not verify.
</compact_output_contract>
