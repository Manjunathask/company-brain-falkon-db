# The bus factor is a graph question

*Draft for the Graph Hacks side prize. Snapshot figures as of 2026-10-16.*

When a maintainer leaves, the obvious question is “Who can take over?” The harder questions are: which parts of the code lose their only active expert, which decisions lose the people who discussed them, and what evidence supports a proposed successor? A code search can find files. A directory of documents can find RFCs. Neither makes the connections between people, work, and decisions explicit enough to answer all three questions reliably.

Bus Factor is a company brain for the public `delta-io/delta` repository, built on FalkorDB. The headline question is **“What does the project lose if this maintainer leaves?”** The app reports exposed Components, decision participation, collaboration context, and likely successors with graph paths beside each result.

We redesigned the first visit for someone who had never seen the project: no sign-in, the live risk number first, then a ranked maintainer search and named questions. Follow-up chips come from returned graph rows rather than model prose. The developer's own test caught a layout bug where the evidence column pushed answers off-screen; fixing the two-column layout kept the answer and its graph visible together.

The graph is the product because these questions depend on relationships. If we remove it, we lose the departure simulation, candidate ranking, file-to-decision paths, and collaboration analysis. The language model can decide which tool to call and describe returned evidence, but it does not manufacture that evidence.

## A repository shaped into evidence

We built a `delta` graph containing people, commits, files, Modules, Components, pull requests, RFC issues, and Decisions. People author commits, commits touch files, files belong to Modules and Components, and commits can link to PRs. PRs reference issues and implement Decisions. CODEOWNERS declarations sit alongside observed expertise, rather than overwriting it. This lets the UI compare who is named as an owner with who recently changed the code.

Components are a finer-grained layer beneath Modules. A large module like `spark` can contain packages with distinct expertise, so the simulator can identify the exposed code area. `KNOWS` holds distinct non-bulk commit counts and last-touch time; `WORKS_WITH` represents recent shared-file overlap; `PARTICIPATED_IN` connects people to decisions through PR and issue activity.

The public snapshot makes the demo reproducible without a GitHub token. On 2026-10-16 it contained 2,240 parsed commits, 3,602 PRs, 19 RFC rows, 220 email-to-login identity mappings, and 4,427 paths present at the checked-out HEAD. Seven gzip JSON inputs preserve the parsed loader inputs and a manifest records the public source, counts, repository SHA, and export time. The total snapshot directory was about 1.65 MiB. The app can reconstruct the graph, derive relationships, and serve locally from this snapshot.

## Three useful queries

The first query ranks a person's `KNOWS` relationships by recent contribution count and reports how many people cover half the area's observed commits. It gives a compact bus-factor view. The distinct-commit count matters: if a single commit changes 30 files, it should count as one contribution, not 30. This query is useful for ranking exposure, but it depends on the selected activity window and thresholds; it is not a staffing forecast.

The departure-impact query starts from current expertise and checks for other active experts above a minimum contribution threshold. Each area is classified as orphaned, at risk, or covered. Related queries show other active contributors who touched the same current files, a starting point for successor candidates. These are heuristics: the strongest overlap does not prove availability or readiness.

The decision-trace query starts from a specific File and walks backward through a Commit, PR, Decision, and RFC Issue. It returns readable properties such as PR number and decision title alongside the path. An `IMPLEMENTS` edge keeps both `via` and `confidence`, so a direct issue reference can be distinguished from a keyword match in a PR title. That distinction is central: plausible association is not the same as documented rationale.

The collaboration views use FalkorDB algorithms too. Betweenness ranks bridges in the recent `WORKS_WITH` network; weakly connected components show groups. For a departure what-if, the app copies the graph with `GRAPH.COPY`, removes the person's `Active` label in the temporary graph, recomputes connectivity, and deletes the copy. Read-only tools use `GRAPH.RO_QUERY`; every query stays in its own `.cypher` file.

## What the data taught us

The repository history needed a few deliberate quality rules. Eight broad commits exceeded the configured bulk-file cutoff and are retained for provenance but excluded from expertise and collaboration calculations. At the initial load, 2,143 historical File nodes were absent at current HEAD; deleting them from the graph would have erased useful history, so each file instead has an `exists` flag. Bot identities remain in the evidence graph but do not count as human expertise. Git emails map to public GitHub author logins when available; explicit noreply identities are used when possible, and all other addresses receive an `email:` key instead of a guessed alias.

Decision links were the least complete source. RFC issue references in commit messages are rare, and PR bodies provide stronger explicit evidence. PR titles can add useful context, but keywords are inherently ambiguous. We store those edges as low confidence and allow tools to require high-confidence evidence. The IcebergCompat demo illustrates the limit: the graph can show candidate paths to a decision, but it cannot honestly claim that those paths explain the validator's design unless the source evidence is explicit.

Memory lives in separate `mem_<user>` graphs and a shared `mem_team` graph. User sessions preserve questions, answers, corrections, and entity references; the watcher records team observations during refresh. `Entity.key` connects memory back to a Component, person, Module, or Decision in the company graph. This separation lets sessions persist and coordinate without blending claims into repository facts.

## Workflow and limits

The implementation/review loop helped keep the graph inspectable. Claude Code (Claude Opus 5.5) reviewed and orchestrated, OpenAI Codex implemented, and the project records briefs, reports, and review rounds under `docs/tasks/`. Each change was checked against focused query tests and, when available, a live FalkorDB graph; review feedback led to bounded evidence paths, confidence filtering, and a more focused departure view. The agent itself calls Claude Sonnet 5.5 at medium effort. In a five-question evaluation, that configuration took 69 seconds and $0.37 total; Opus 5.5 at medium took 112 seconds and $1.17, while low effort missed one ambiguous question.

This is not a complete picture of Delta Lake's knowledge. The graph covers a two-year commit window plus RFCs and associated public PR and issue data. It does not read private discussions, understand code semantics, or capture every design conversation. Git history records changes, not ownership, skill, or availability. A title match is only a lead; the simulator should prompt follow-up, not decide an org chart.

When the system cannot establish a reason, it should show the path and say what remains unknown. That honesty is part of the feature.
