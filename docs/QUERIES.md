# Cypher query guide

One entry per query file. Parameters are passed by the Python tool registry; timestamps are epoch milliseconds.

## `00_counts.cypher`

**What it answers:** report total node and relationship counts for a graph.

**Parameters:** none.

Two small subqueries count all nodes and all relationships independently, then return them in one row. The loader uses this for its progress summaries.

## `00_indexes.cypher`

**What it answers:** prepare stable lookup keys for every node type loaded in this package.

**Parameters:** none.

These indexes support stable lookups by each node type key. The two full-text indexes let FalkorDB search decision and PR titles without moving search outside the graph.

## `01_load_commits.cypher`

**What it answers:** load people, commits, touched files, modules, and components from local git history.

**Parameters:** $rows is a batch of commit maps with author, authorEmail, authorHandle, authorBot, authorName, files, and commit fields; each file has module and component.

The loader merges people, commits, files, modules, and components from batched rows. Stable keys make reruns safe, and each commit records the files it touched.

## `01b_link_part_of.cypher`

**What it answers:** link loaded commits to any PR nodes whose numbers match Commit.pr.

**Parameters:** none; the PR and Commit.pr properties must already be loaded.

Commit subjects carry PR numbers, so this query joins commits to already loaded pull requests. It uses an optional match so commits without a PR remain intact.

## `01c_load_prs.cypher`

**What it answers:** load GitHub pull requests and their opener/reviewer people.

**Parameters:** $rows has PR properties, author/login handle/bot fields, and reviewers as {login, handle, bot, at} maps.

This batch creates pull requests and their author and reviewer activity edges. Relationship timestamps are updated so activity recency reflects the newest review.

## `01d_load_issues.cypher`

**What it answers:** load the RFC tracking issues and people who opened or commented on them.

**Parameters:** $rows has issue properties, author/login handle/bot fields, and commenters as {login, handle, bot, at} maps.

This batch loads RFC issues and the people who opened or commented on them. The issue nodes provide the discussion endpoint for decision traces.

## `01e_link_references.cypher`

**What it answers:** connect PRs to referenced RFC issues that are already represented in the graph.

**Parameters:** $rows contains {pr, issue} number pairs extracted from PR bodies.

Explicit issue references in PR bodies become graph edges. These links later provide high-confidence evidence that a PR implements a decision.

## `01f_cleanup_components.cypher`

**What it answers:** remove Component nodes left without any File membership after a path-rule update.

**Parameters:** none.

This cleanup removes Components no longer referenced by files. It keeps the derived hierarchy aligned after component path rules change.

## `01g_component_activity.cypher`

**What it answers:** rank Components by recent authored file touches for the path-mapping report.

**Parameters:** $since is an epoch-millisecond activity cutoff.

It traverses recent authored commits through touched files into Components and counts file touches. The result ranks the busiest Components for the path mapping report.

## `01h_component_count.cypher`

**What it answers:** count Component nodes after path mapping.

**Parameters:** none.

The query counts Component nodes after ingestion and cleanup. It provides the total printed beside the component activity report.

## `02_load_decisions.cypher`

**What it answers:** load RFC decisions, their tracking issues, and RFC document files.

**Parameters:** $rows is a batch of RFC maps with slug, title, status, proposedOn, decidedOn, issue, path, module, and component.

The RFC table rows become Decision nodes linked to their issue and markdown file. The table supplies status and dates without LLM extraction.

## `02b_superseded_by.cypher`

**What it answers:** record that Managed Commits was superseded by Catalog-Managed Tables.

**Parameters:** none.

This query records the known replacement relationship between rejected Managed Commits and accepted Catalog-Managed Tables. The source property preserves the PR evidence.

## `02c_load_codeowners.cypher`

**What it answers:** load declared CODEOWNERS handles and the modules covered by each rule.

**Parameters:** $rows contains {pattern, module, owners}; owners has {login, handle} maps.

Declared CODEOWNERS patterns become module-level owner edges. These are kept separate from observed commit expertise for comparison.

## `03_derive_knows.cypher`

**What it answers:** derive each non-bot person's commit expertise and most recent touch per module.

**Parameters:** none.

For each person and Module, count distinct commits and retain the latest touch. Counting distinct commits prevents multi-file commits from inflating expertise.

## `03b_derive_last_seen.cypher`

**What it answers:** refresh each person's last commit/activity time and the Active label for the requested window; reviews count because maintainers can contribute without committing.

**Parameters:** $since is the activity cutoff in epoch milliseconds.

This query combines commit, PR, review, and issue activity timestamps. It refreshes the Active label for people with any recent contribution.

## `03c_derive_knows_component.cypher`

**What it answers:** derive each non-bot person's expertise and latest touch per Component.

**Parameters:** none.

This is the Component-level expertise version of KNOWS. It counts distinct authored commits touching files in each Component.

## `03g_sanity_top_modules.cypher`

**What it answers:** list Modules with the most derived KNOWS edges for derive sanity reporting.

**Parameters:** none.

It aggregates KNOWS relationships by Module and orders the counts from largest to smallest. The derive command uses these rows to check that module expertise was refreshed.

## `03h_sanity_top_components.cypher`

**What it answers:** list Components with the most derived KNOWS edges for derive sanity reporting.

**Parameters:** none.

It aggregates KNOWS relationships by Component and returns the ten largest counts. This checks the finer-grained expertise derivation independently from Module totals.

## `03i_sanity_active_count.cypher`

**What it answers:** count people marked Active after the derive pass.

**Parameters:** none.

This counts Person nodes carrying Active after the derive pass. The label is based on recent commit, PR, review, or issue activity.

## `03j_sanity_works_count.cypher`

**What it answers:** count derived WORKS_WITH relationships.

**Parameters:** none.

This counts the graph?s WORKS_WITH edges. The derive command prints it to show the size of the collaboration projection.

## `03k_sanity_top_pairs.cypher`

**What it answers:** list the five strongest WORKS_WITH pairs.

**Parameters:** none.

The query orders collaboration edges by their shared-file counts and returns the five strongest pairs. Stable logins break ties for repeatable output.

## `03l_sanity_participation.cypher`

**What it answers:** count participating people for each decision.

**Parameters:** none.

Each Decision is retained through an optional participant match, including decisions with no participants. The result counts participation edges per decision.

## `03m_sanity_relationship_count.cypher`

**What it answers:** count all graph relationships after a derive query.

**Parameters:** none.

This aggregates all relationships after each derive step. The printed total helps identify whether the step produced or removed edges.

## `04_derive_works_with.cypher`

**What it answers:** derive recent collaboration between non-bot people from files both edited.

**Parameters:** $since is the epoch-millisecond window start, $minShared is the minimum shared files, and $maxFileCommits excludes hub files touched by too many commits in that window.

People become collaborators when they edited the same recent, non-hub files. The query excludes bots and replaces prior derived edges on rerun.

## `04b_derive_participated_pr.cypher`

**What it answers:** mark non-bot people who opened or reviewed a PR that implements a decision.

**Parameters:** none.

Authors and reviewers of PRs linked to decisions become participants. IMPLEMENTS confidence carries forward as the participation confidence.

## `04c_derive_participated_issue.cypher`

**What it answers:** mark non-bot people who opened or commented on an RFC issue tracked by a decision.

**Parameters:** none.

People opening or commenting on an RFC issue count as high-confidence participants in the linked decision. Existing PR participation evidence is preserved.

## `04d_derive_implements_issue_ref.cypher`

**What it answers:** link PRs to decisions whose tracked RFC issue the PR body references.

**Parameters:** none.

This follows explicit PR-to-issue references into RFC decisions. That path is considered high-confidence and records its source for explanation.

## `04e_derive_implements_rfc_doc.cypher`

**What it answers:** link PRs that changed an RFC markdown document to that RFC's decision.

**Parameters:** none.

A PR that changes the RFC markdown file is linked to the corresponding decision by slug. This is a high-confidence document trail.

## `04f_load_implements_keyword.cypher`

**What it answers:** load low-confidence title keyword links from the curated Python matcher.

**Parameters:** $rows contains {pr, slug, pattern} matches.

The precomputed, word-boundary keyword matches create lower-confidence PR-to-decision links. The edge retains source history and avoids downgrading stronger evidence.

## `04g_link_pr_titles.cypher`

**What it answers:** load PR number and title pairs for the curated decision keyword matcher.

**Parameters:** none.

It reads each loaded PR?s number and title from the graph. The local keyword matcher uses these graph rows as inputs for curated decision links.

## `04h_implements_counts_by_via.cypher`

**What it answers:** count IMPLEMENTS edges by evidence source.

**Parameters:** none.

The query groups IMPLEMENTS relationships by their evidence source. This reports how many links came from issue references, RFC documents, or title keywords.

## `04i_implements_counts_by_decision.cypher`

**What it answers:** count IMPLEMENTS edges for every Decision, including decisions without links.

**Parameters:** none.

An optional match preserves decisions with no implementation links. The grouped counts expose which decisions have little or no PR evidence.

## `04j_recent_implements.cypher`

**What it answers:** return the three most recent PR implementations for one decision.

**Parameters:** $slug is the Decision slug.

It follows IMPLEMENTS from one decision to its PRs and orders them by merge time, then PR number. The output gives the reviewer recent examples and their confidence source.

## `04k_delete_stale_keyword_links.cypher`

**What it answers:** remove stale title-keyword-only IMPLEMENTS links before rebuilding curated matches.

**Parameters:** none.

The deletion targets only IMPLEMENTS edges whose sole source is the curated title keyword. Edges with issue or RFC-document evidence remain intact.

## `05_bus_factor.cypher`

**What it answers:** calculate how many people cover half of recent commit expertise in each Module.

**Parameters:** $since is the activity-window start in epoch milliseconds; $minCommits is the minimum person expertise; $minTotal is the minimum module commit total to report.

This ranks Module expertise by recent KNOWS commit counts and finds how many leading people cover half of the total. Small modules are reported through the filtered count.

## `05_bus_factor_graph.cypher`

**What it answers:** show each reported Module and the top experts counted toward its busFactor.

**Parameters:** $areas contains {name, count}; $since, $minCommits, and $minTotal match the table filters.

For each reported Module, the query ranks eligible KNOWS edges by commit count and keeps exactly the first busFactor people. Each returned path connects an expert to the Module whose total they contribute to.

## `05b_bus_factor_component.cypher`

**What it answers:** calculate how many people cover half of recent commit expertise in each Component.

**Parameters:** $since is the activity-window start in epoch milliseconds; $minCommits is the minimum person expertise; $minTotal is the minimum component commit total to report.

This applies the same half-coverage calculation at Component level. Component-level results expose the narrower areas that can be hidden inside a Module.

## `05b_bus_factor_component_graph.cypher`

**What it answers:** show each reported Component and the top experts counted toward its busFactor.

**Parameters:** $areas contains {name, count}; $since, $minCommits, and $minTotal match the table filters.

For each reported Component, the query ranks eligible KNOWS edges and retains the number of experts used by its busFactor. The returned paths show precisely those people and their expertise links.

## `06_departure_impact.cypher`

**What it answers:** classify the departing person's recent Component expertise by the active experts who remain.

**Parameters:** $login is the departing person; $since is the activity-window start in epoch milliseconds; $minCommits is the minimum remaining expertise.

This lists Components known by the departing person and counts active non-bot experts who remain. Zero remaining experts means orphaned expertise.

## `06_departure_impact_graph.cypher`

**What it answers:** show the departing person, affected Components, and active experts who remain.

**Parameters:** $login and $components are the departing person and returned Component names.

The query returns a KNOWS path from the departing person to every affected Component, plus paths from active experts who remain. This lets the UI show the coverage behind each risk row.

## `06b_departure_files.cypher`

**What it answers:** group files touched by a departing person that no other active, non-bot person touched recently.

**Parameters:** $login is the departing person; $since is the activity-window start in epoch milliseconds.

This finds recently touched files that no other active non-bot person edited. It aggregates editors by file before deciding which files are orphaned.

## `06b_departure_files_graph.cypher`

**What it answers:** show the exact orphaned files reported for a departing person, with their source commits and Components.

**Parameters:** $login is the person; $since is the activity cutoff.

It repeats the orphan test at file level, requiring a recent commit by the departing person and no recent edit by another active non-bot. The returned paths connect that person through the touching commit and orphaned file to its Component.

## `07_orphaned_decisions.cypher`

**What it answers:** find decisions for which the departing person is the only currently active participant at the requested evidence confidence.

**Parameters:** $login is the person; $minConfidence is 'high' or 'low'.

This filters the departing person?s decision participation by confidence, then checks whether any other active participant meets that same threshold. It returns isolated decisions and possible people to ask.

## `07_orphaned_decisions_graph.cypher`

**What it answers:** show the departing person's participation in each orphaned Decision and every qualifying person to ask.

**Parameters:** $login, $decisions, and $minConfidence select the result evidence.

The query follows confidence-qualified participation from the departing person to each selected Decision, then returns paths from other qualifying participants into those Decisions. These paths support the decision and who-to-ask evidence.

## `08_successor.cypher`

**What it answers:** rank active non-bot successors for a departing person's Component by shared recent files, then component commits.

**Parameters:** $login is the departing person; $component is the Component.name; $since is the recent activity cutoff.

The departing person?s recent files in one Component form the overlap set. Active non-bot candidates are ranked by how many of those files they touched, then by their KNOWS commit total.

## `08_successor_graph.cypher`

**What it answers:** show only the shared recent files linking the departing person and ranked successor candidates.

**Parameters:** $login, $successors, $component, and $since identify the overlap result.

The path starts at the departing person, passes through their recent commit and a shared file, then follows the candidate?s touching commit to that person. It restricts paths to the selected Component and ranked successors so the evidence matches the overlap that drove the result.

## `09_bridges.cypher`

**What it answers:** rank active non-bot people by betweenness in the recent WORKS_WITH network.

**Parameters:** $limit is the maximum number of people returned.

FalkorDB?s betweenness algorithm scores Active people over WORKS_WITH edges. The query sorts those scores so the most structurally important collaborators appear first.

## `09_bridges_graph.cypher`

**What it answers:** show top bridge people, their WORKS_WITH neighbors, and the relationships among those nodes.

**Parameters:** $people contains the top betweenness logins.

Starting from the highest betweenness people, it expands one WORKS_WITH edge to show their local collaboration context. The 200-row cap keeps the UI subgraph bounded.

## `09b_groups.cypher`

**What it answers:** count active collaboration groups, the largest group, and groups with more than one person.

**Parameters:** none.

WCC assigns component IDs to active people, including isolated people, and the query summarizes each component?s size. It reports the largest group and counts only components with more than one person as non-singleton groups.

## `09b_groups_graph.cypher`

**What it answers:** show the largest active collaboration group and its internal WORKS_WITH edges.

**Parameters:** none.

WCC first groups active people, then the query selects the largest member collection. It returns only WORKS_WITH relationships inside that group and caps the rendered subgraph at 200 edges.

## `09c_whatif_membership.cypher`

**What it answers:** map each active person with at least one active WORKS_WITH edge to their WCC component.

**Parameters:** none; run against the temporary what-if graph before and after removing Active.

FalkorDB WCC assigns components on the temporary graph. A follow-up relationship match removes isolated Active people from these connectivity metrics so the largest group describes actual collaborators.

## `09d_whatif_remove_active.cypher`

**What it answers:** remove one person's Active label only in the temporary what-if graph.

**Parameters:** $login is the person being simulated as departed.

The query matches the departing login and removes its Active label. The simulator runs it only on its temporary collaboration graph before recalculating WCC.

## `09e_whatif_graph.cypher`

**What it answers:** show the departing person, their direct collaborators, and people cut off from the largest surviving group.

**Parameters:** $people is the set of login keys selected by the simulation.

The simulator passes the departing person, direct collaborators, and cut-off people as stable login keys. The query returns only WORKS_WITH edges whose endpoints are in that evidence set, with a 200-row cap.

## `09f_whatif_collaborators.cypher`

**What it answers:** list a person's active, non-bot direct WORKS_WITH collaborators before departure.

**Parameters:** $login is the person being simulated.

The query follows WORKS_WITH in either direction from the departing person and filters to active non-bot neighbors. It returns distinct logins so the simulator can report a direct collaborator count.

## `10_decision_trace.cypher`

**What it answers:** show recent file-to-decision evidence paths, including how each PR was linked to the decision.

**Parameters:** $path is the exact File.path; $limit is the maximum paths.

Starting at the requested file, this path walks backward through a commit and PR into a decision and its RFC issue. The result includes the IMPLEMENTS confidence and source, preferring stronger links before recency.

## `10b_why_not.cypher`

**What it answers:** explain which accepted decision replaced a rejected decision and who can explain the replacement.

**Parameters:** $slug is the rejected Decision.slug.

This follows SUPERSEDED_BY from the rejected choice to its replacement and issue. Participants on the replacement decision are gathered as people who can explain it.

## `10b_why_not_graph.cypher`

**What it answers:** show a rejected Decision's replacement, tracking Issue, and people who participated in the replacement.

**Parameters:** $slug is the rejected Decision slug.

This returns the rejected and replacement decisions, their issue, and participant context.

## `11_drift.cypher`

**What it answers:** count code changes since accepted decisions were made and identify editors who did not participate.

**Parameters:** $minConfidence defaults to 'high'; only implementations at or above the threshold are included.

For accepted decisions, this follows qualifying IMPLEMENTS edges to the files behind them and counts later edits. Editors who did not participate in the decision are counted separately.

## `11_drift_graph.cypher`

**What it answers:** show accepted-decision implementation paths and later edits on the files behind them.

**Parameters:** $decisions are selected titles; $minConfidence is the implementation threshold.

This returns accepted decisions and adjacent PR, file, and participant evidence for the drift summary.

## `12_declared_vs_actual.cypher`

**What it answers:** compare module-level CODEOWNERS declarations with the top three recent, non-bot commit experts.

**Parameters:** $since is the activity-window cutoff; $minCommits is minimum KNOWS commits.

The query collects CODEOWNERS declarations, ranks recent non-bot Module expertise by KNOWS commits, and shows which declared owners are absent from the top three.

## `12_declared_vs_actual_graph.cypher`

**What it answers:** show declared owners and the top three observed experts for each reported Module.

**Parameters:** $areas contains {name, actualTop3}; $modules are the returned Module names.

This returns each Module, its declared owners, and its observed experts as a small evidence subgraph.

## `13_find_entity.cypher`

**What it answers:** resolve free text to people, modules, Components, decisions, or files using graph indexes and string matching.

**Parameters:** $text is the case-insensitive query string; $limit caps results per entity type.

This searches case-folded logins and names, Module and Component names, Decision titles and slugs, and file path suffixes. All candidates are graph nodes with typed keys so later tools can resolve them.

## `13_find_entity_graph.cypher`

**What it answers:** return only the graph entities matched by find_entity, with no neighboring edges.

**Parameters:** $people, $components, $modules, $decisions, and $files are matched keys.

The query matches each result by its label-specific stable key and returns the matching nodes only. It deliberately leaves neighborhood expansion to later graph tools so entity search stays uncluttered.
