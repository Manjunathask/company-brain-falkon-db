# The bus factor is a graph question

*Draft for the Graph Hacks side prize. Figures from the live graph on 2026-10-17.*

When a maintainer leaves, the obvious question is “Who can take over?” The harder questions are which parts of the code lose their only recent author, which decisions lose the people who discussed them, what evidence supports a successor, and what should be handed over before the person goes. A code search finds files and a folder of documents finds RFCs, but neither connects people, work and decisions well enough to answer those questions.

Bus Factor is a company brain for the public `delta-io/delta` repository, built on FalkorDB. It answers **“What does the project lose if this maintainer leaves?”**, shows the graph path behind each result, and drafts a sourced handover plan for an exposed area.

The graph is the product because every one of these answers is a relationship. Remove FalkorDB and the departure view, successor evidence, decision traces, handover packets and shared memory all go. The language model picks tools and summarises their rows; it does not produce the evidence.

## A repository shaped into evidence

The `delta` graph holds people, commits, files, Modules, Components, pull requests, reviews, RFC issues and Decisions. People author commits, commits touch files, files belong to Components (packages inside a Module), commits belong to PRs, people review PRs, and PRs reference issues and implement Decisions. CODEOWNERS declarations sit next to observed work rather than overwriting it.

A checked-in public snapshot (2,240 commits, 3,602 PRs, 19 RFCs and their tracking issues, 220 identity mappings, 4,427 current paths, about 1.7 MiB gzipped) rebuilds the graph in seconds, so judges need no GitHub token.

## Our first headline was wrong

Our landing page said 42 of 87 active code areas had a bus factor of 1, “in the last 12 months”. A pre-submission review, which we then checked against the live graph, found that the query filtered people by their latest commit but used their commit count over the whole two years. Counting only commits inside the window gives **25 of 69**. The same review found that a leaving person needed just one commit in an area for it to be called orphaned: four of one maintainer's five “orphaned” areas rested on a single commit.

The fix was a query change, not a model change: count in-window commits straight from `AUTHORED` and `TOUCHED`, and apply the same 2-commit threshold to everyone. Because every number lives in a `.cypher` file, the mistake was findable in minutes. That is the strongest argument we know for keeping the queries visible.

The review also asked a better question: authorship is one signal, so who reviewed that code? Every area with no other recent author held by the 15 most active people turned out to have between 2 and 11 active reviewers. “Nobody else wrote this” is not “nobody else knows this”. The app now shows reviewers beside each risk label, never folded into it, and labels areas `NO OTHER AUTHOR` instead of “orphaned”.

## From finding to handover

For an exposed area, **Draft handover** builds a packet from four queries in under 0.1 s. Candidates are recent authors plus recent reviewers of the area's PRs. Each kind of evidence is its own column, ranked by a plain sort: reviews of the leaving person's PRs first, because that reviewer has already seen the changes. For Hao Jiang's `flink/inttest`, the suggestion is scottsand-db: “Reviewed 2 of Hao Jiang's 3 PRs here; no commits of their own here yet; took part in Catalog-Managed Tables.” The packet adds the PRs to read first, the decisions to preserve with links and quoted reasons, and questions for the person leaving, each tied to the row it came from.

Decision links needed the same honesty. Of 283 PR-to-decision links, 230 come from a keyword in the PR title. Every card now separates explicit links from title matches and calls the latter keyword guesses. Where a source states a reason, we quote it: the Managed Commits rejection is quoted verbatim from tracking issue #4381, parsed at load time rather than written by a model.

## Memory that changes the answer

Memory lives in separate graphs: `mem_v_<id>` per anonymous visitor and a shared `mem_team`, joined to the company graph by `Entity.key` in Python because Cypher does not cross graphs. A saved handover plan goes into `mem_team`. When someone marks scottsand-db unavailable (“on leave until January”), on the page or by telling the chat agent, the next packet skips that person, labels the note unverified, and says what changed: the suggestion moves to kaiqijinwow. Asked for the same handover, the chat agent's `handover_plan` tool reads the same note. Team claims never become repository facts.

## Three queries worth reading

The bus-factor query counts each person's distinct in-window commits per area, sorts them, and reduces until half the total is covered. Distinct commits matter: one commit touching 30 files is one contribution.

The departure query collects remaining authors and active reviewers in separate stages, so one count cannot multiply the other, a FalkorDB lesson we learned the hard way: aggregate with `count(DISTINCT …)` before the next match.

The collaboration what-if copies the graph with `GRAPH.COPY`, removes the person's `Active` label in the copy, recomputes `algo.WCC` groups and `algo.betweenness` bridges, and deletes the copy. Read-only tools run through `GRAPH.RO_QUERY`.

## What the data taught us

Eight broad commits are kept for history but excluded from expertise. Files deleted since a commit stay as nodes with `exists=false` instead of disappearing. Bots stay visible but never count as human expertise. Git emails map to public GitHub logins where GitHub says so, and otherwise get an `email:` key rather than a guessed alias.

## Workflow and limits

I set the direction and made the calls: the plan and data source, Sonnet over Opus for the agent, the newcomer testing that reshaped the UI, and which review findings to act on. The AI tools wrote the code. Claude Code (Claude Opus 5.5) planned and reviewed; OpenAI Codex implemented most work packages; Codex on GPT-6-Astra reviewed the project before submission. When Codex ran out of usage, Claude Code finished the measurement fixes and built the evidence and handover packages. Every brief, report and review is in `docs/tasks/`. The running agent uses Claude Sonnet 5.5.

This is not a complete picture of Delta Lake's knowledge. The graph covers two years of public commits, PRs, reviews and RFCs. It cannot read private discussions, judge code quality, or know who is available. A suggested successor is a lead for a conversation, not a decision. When the system cannot establish a reason, it should show the path and say what remains unknown. That honesty is part of the feature.
