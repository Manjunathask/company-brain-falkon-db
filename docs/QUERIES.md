# Cypher query guide

## `18_handover_candidates.cypher`

**What it answers:** Who could take over one code area from a leaving person, with each kind of evidence in its own column.

**Parameters:** $login, $component, $since (epoch ms), $exclude (logins marked unavailable in team memory), $limit.

Collect the leaving person's in-window, non-bulk commits on current files in the area, their files and their PRs. The candidate pool is recent Active authors of the area plus recent reviewers of PRs that touched it, so an area with no other author still gets candidates from reviews. Each column is aggregated in its own `WITH` stage with `count(DISTINCT ...)`: `reviewedTheirPRs` (the leaving person's PRs here that the candidate reviewed), `sharedFiles`/`outOf`, `areaCommits`, `areaReviews`, `sharedDecisions` (high-confidence participation in decisions linked to the area) and `toLearn` (files only the leaving person edited here that the candidate never authored). The order is a plain sort, not a weighted score: reviews of this person's PRs first, because that reviewer has already seen these changes. People in `$exclude` come back last with `skipped = true`, so the packet can say why they were left out.

## `18b_handover_reading.cypher`

**What it answers:** Which of the leaving person's recent PRs in one area a successor should read first.

**Parameters:** $login, $component, $since (epoch ms), $limit.

Group the person's in-window, non-bulk commits on current area files by PR, then add decision links (with confidence) and reviewers in separate stages. PRs with an explicit decision link come first, then the most area files touched, then the most recently merged.

## `18c_handover_decisions.cypher`

**What it answers:** Which RFC decisions a successor must preserve in one area, with their sources and who else took part.

**Parameters:** $login, $component.

Find decisions linked to the area through Commit -PART_OF-> PR -IMPLEMENTS-> Decision over all loaded history, or through an RFC document filed in the area. Count explicit and title-match PRs per decision, then add the tracking issue and RFC path (for links), whether the leaving person took part, other active high-confidence participants, and the SUPERSEDED_BY reason from either end of the edge. At most five, explicit links first.

## `18e_handover_activity_since.cypher`

**What it answers:** How much work landed in one area after a saved handover packet.

**Parameters:** $component, $since (the saved packet's time, epoch ms).

Counts distinct non-bulk commits on current area files after `$since` and the PRs they belong to. The packet uses it to explain why a new suggestion differs from the saved one.

## `18_handover_graph.cypher`

**What it answers:** The paths behind one handover packet.

**Parameters:** $login, $component, $prs (reading-list PR numbers), $candidates (listed candidate logins).

A union of short paths with no Commit or File nodes: the leaving person's reading PRs, their decision links, candidate reviews of those PRs, and KNOWS edges to the area. It is drawn beside the packet.

## `16e_team_write_availability.cypher`

**What it answers:** Record in shared team memory that a person is or is not available for handover work.

**Parameters:** $id, $agent, $key (person:<login>), $status, $reason, $text, $ts, $source.

One Observation of kind `availability` per note; notes are never edited and the newest one per person wins. The writer is `chat:<visitor>` for the web page and the chat agent, so "Start over" removes that visitor's notes with their other claims. These are unverified notes and never change the delta graph.

## `16f_team_availability.cypher`

**What it answers:** The latest availability note for every person who has one.

**Parameters:** none.

Orders each person's availability observations newest first and keeps the first. The packet builder treats status `unavailable` as `$exclude` for `18_handover_candidates`, joining team memory to delta by login in Python because Cypher cannot cross graphs.

## `16g_team_write_handover.cypher`

**What it answers:** Save a drafted handover packet to shared team memory.

**Parameters:** $id, $agent, $key (component:<name>), $person, $candidate, $text, $ts, $source.

One Observation of kind `handover` about the component, recording who is leaving and who was suggested. Other visitors and later sessions read it back with 16h.

## `16h_team_last_handover.cypher`

**What it answers:** The most recently saved handover packet for one leaving person and one component.

**Parameters:** $key (component:<name>), $person.

One row, newest first. The packet compares its own suggestion with this one and says what changed: a candidate marked unavailable, or new activity in the area (18e).

## `17c_active_person.cypher`

**What it answers:** Whether a login is an active, non-bot person, and their display name.

**Parameters:** $login.

Used by the departure and handover endpoints to return 404 for unknown people and to show the leaving person's name, and by the agent's name check (WP15) before any tool that takes a login runs.

## `17d_component_exists.cypher`

**What it answers:** Whether a code area with this exact name exists.

**Parameters:** $component.

Used by the handover endpoint to return 404 for an unknown area, and by the agent's name check before `successor` and `handover_plan` run.

## `17_people_search.cypher`

**What it answers:** search Active non-bot maintainers by recent authored commit activity.

**Parameters:** $q is a case-insensitive login or name fragment; $since is an epoch-millisecond cutoff; $limit is 1..25.

Distinct non-bulk commits are counted per person. Login/name prefixes rank ahead of contains matches, with recent commit count and login breaking ties.

## `17b_team_delete_visitor_claims.cypher`

**What it answers:** delete team-memory observations belonging to an anonymous visitor and report the number removed.

**Parameters:** $agent is the validated `chat:v_<32 lowercase hex>` agent name.

The query deletes only observations attached to that Agent and removes the Agent node, leaving other users' claims intact.

One entry per query file. Parameters are passed by the Python tool registry; timestamps are epoch milliseconds.

## `14_mem_record_episode.cypher`

**What it answers:** save a question and answer in a user's memory graph, linked to graph entities it touched.

**Parameters:** $sessionId, $text, $ts, $answer, $tools, and $entityKeys.

It merges the session and creates one Question per ask. Empty entity lists still record the episode.

## `14b_mem_store_correction.cypher`

**What it answers:** store a user-provided correction against a stable entity key.

**Parameters:** $key, $text, $ts, and $source.

The correction is a separate node with provenance and cannot modify the `delta` graph.

## `14c_mem_recall.cypher`

**What it answers:** retrieve questions and corrections for explicit entity keys, or the latest five episodes when no keys are supplied.

**Parameters:** $keys and $limit.

The query stays within one user's memory graph; Python joins each returned entity key to `delta` for change checks.

## `14d_changed_since.cypher`

**What it answers:** list commits and PRs connected to a person, Component, Module, or Decision since a timestamp.

**Parameters:** $kind, $key, and $since (epoch milliseconds).

All traversals run on the `delta` graph and return a zero-count row when no newer evidence exists.

## `15_refresh_watermarks.cypher`

**What it answers:** return the latest loaded Commit timestamp and PR update timestamp.

**Parameters:** none.

Independent optional matches preserve one row for an empty graph, letting refresh use either timestamp as a strict incremental watermark.

## `15a_refresh_head_files.cypher`

**What it answers:** recompute `File.exists` from the current repository HEAD snapshot.

**Parameters:** $paths is the normalized list of paths present at HEAD.

The update visits every known file so deletions are reflected even on a refresh with no new commits; historical File and TOUCHED nodes remain available.

## `15b_refresh_component_risk.cypher`

**What it answers:** Count each Component's qualifying recent authors before and after a refresh.

**Parameters:** $since (epoch ms); the qualifying-author threshold is fixed at 2 commits.

Count distinct in-window non-bulk commits on current files per Active non-bot author, rather than all-history KNOWS totals. Collect authors with at least two commits and retain empty Components. Refresh has no leaving person, so it returns `recentAuthors` and refresh.py reports changes as author counts (0, 1, 2+), not as the departure risk codes. Older team-memory observations that used the retired codes are shown in the same author-count terms; the stored text is not edited.

## `16_team_write_observation.cypher`

**What it answers:** write an idempotent shared observation for an entity in `mem_team`.

**Parameters:** $id, $agent, $text, $ts, $kind, $source, and $key.

Stable observation IDs make watcher retries safe; `Entity.key` lets Python join memory to the separate Delta graph.

## `16b_team_recall.cypher`

**What it answers:** retrieve observations about selected entities plus the newest five team observations.

**Parameters:** $keys is a list of entity keys such as `component:kernel/kernel-api`.

It runs only in `mem_team`; Python supplies resolved keys and deduplicates the entity-specific and recent context.

## `16c_team_record_refresh.cypher`

**What it answers:** persist a RefreshRun record and connect the observations produced by that run.

**Parameters:** $id, $ts, $newCommits, $newPRs, and $observationIds.

The run ID is stable for the refresh timestamp, and each observed note is matched by its deterministic ID.

## `16d_team_list.cypher`

**What it answers:** return recent shared observations and refresh summaries for `GET /api/team`.

**Parameters:** $limit caps both result lists.

Observations and refresh runs are collected independently to avoid multiplying rows when both collections have several entries.

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

The loader merges people, commits, files, modules, and components from batched rows. Stable keys make reruns safe, and each commit records the files it touched. After the file unwind, rows keep only the commit node, the file map and the file node: carrying the whole commit row copied its file list onto every file row, and the snapshot load peaked at 681 MB instead of 51 MB.

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

**Parameters:** $rows has issue properties (title, state, createdAt, body), author/login handle/bot fields, and commenters as {login, handle, bot, at} maps.

This batch loads RFC issues and the people who opened or commented on them. The issue nodes provide the discussion endpoint for decision traces, and the issue body is kept so a decision's stated reason can be quoted from its source.

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

**What it answers:** record that one decision was superseded by another, with the evidence and the stated reason.

**Parameters:** $old, $new (Decision slugs), $source, $rationale, $rationaleSource.

load.py passes the one known pair: rejected Managed Commits was replaced by Catalog-Managed Tables, with PR #4382 as evidence. The rationale is a verbatim excerpt parsed at load time (`rationale_excerpt` in ingest/rfcs.py): the first paragraph of tracking issue #4381 that names the old RFC (its keyword patterns or issue #2598), plus the list right after it. No LLM writes it; it is null when the cached issue has no body.

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

## `03d_mark_bulk_commits.cypher`

**What it answers:** mark commits that touched more than the configured file threshold as bulk changes.

**Parameters:** $maxCommitFiles is the maximum number of touched files for a commit to contribute to expertise and collaboration.

The query resets and recomputes `Commit.bulk` from distinct TOUCHED files. Bulk commits stay in the graph for PR decision traces, while derived expertise and overlap queries exclude them.

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

**What it answers:** Compute the fewest authors covering at least half of a Module's qualifying recent commits.

**Parameters:** $since (epoch ms), $minCommits per author, $minTotal per area.

KNOWS totals cover all loaded history, so traverse AUTHORED -> Commit -> TOUCHED -> current File -> IN_MODULE. Exclude bots and bulk commits, count distinct commits per person/module before applying thresholds and ranking, then reduce until half the total is covered. Return countedExperts for the exact authors included in that reduction.

## `05_bus_factor_graph.cypher`

**What it answers:** Show the exact Module authors counted by the bus-factor table.

**Parameters:** $areas contains {name, countedExperts}.

Return KNOWS paths only for the table-selected logins, without re-ranking historical KNOWS counts. The edges establish area membership; the table supplies the recent counts.

## `05b_bus_factor_component.cypher`

**What it answers:** Compute the fewest authors covering at least half of a Component's qualifying recent commits.

**Parameters:** $since (epoch ms), $minCommits per author, $minTotal per area, $includeTestResources.

Traverse authored in-window commits through current files into Components instead of using all-history KNOWS totals. Exclude bots/bulk commits and optionally test-resource areas, aggregate distinct commits per person/area before ranking, and return countedExperts from the half-total reduction.

## `05b_bus_factor_component_graph.cypher`

**What it answers:** Show the exact Component authors counted by the bus-factor table.

**Parameters:** $areas contains {name, countedExperts}.

Return KNOWS paths only for the table-selected logins, without re-ranking historical KNOWS counts. No global path limit silently drops counted authors.

## `06_departure_impact.cypher`

**What it answers:** Report recent author coverage after a person leaves, with a separate active-reviewer signal.

**Parameters:** $login, $since (epoch ms), $minCommits on both author sides, $componentPrefix, $includeTestResources.

Count distinct in-window, non-bulk commits on current files directly, because KNOWS totals are all-history. Omit areas where the leaving non-bot author fails the threshold; aggregate other Active non-bot authors before matching reviewers. NO OTHER AUTHOR / ONE OTHER AUTHOR / COVERED mean zero / one / at least two remaining qualifying authors. Reviewers must be Active, non-bot, another person, and have REVIEWED.at > $since on a PR with an in-window non-bulk commit touching a current area file. Count distinct area PRs per reviewer, return up to five logins ordered by PR count then login (`reviewers`), the same five with their PR counts (`reviewerPRs`), and the full reviewerCount; reviews do not change risk. The departure graph draws reviewerPRs as one collapsed REVIEWED_IN edge per reviewer and area.

## `06_departure_impact_graph.cypher`

**What it answers:** Show exactly the departure table's authors and listed reviewers.

**Parameters:** $login, $areas containing {name, remaining, reviewers}, $since (epoch ms).

Use the leaving login plus each row's remaining logins for KNOWS paths. Anchor the review traversal at each Component, deduplicate qualifying PRs before matching listed reviewers, and keep up to three PRs per reviewer/area (highest PR numbers first). Return REVIEWED -> PR paths separately; do not broaden table membership.

## `06b_departure_files.cypher`

**What it answers:** group files touched by a departing person that no other active, non-bot person touched recently.

**Parameters:** $login is the departing person; $since is the activity-window start in epoch milliseconds; $componentPrefix optionally narrows component names; $includeTestResources defaults to false.

This finds recently touched, extant files touched by focused commits that no other active non-bot person edited. Deleted files retain their TOUCHED history but cannot count as current knowledge at risk.

## `06b_departure_files_graph.cypher`

**What it answers:** show the exact orphaned files reported for a departing person, with their source commits and Components.

**Parameters:** $login is the person; $since is the activity cutoff.

It repeats the orphan test while excluding deleted files and bulk commits, and requires no recent edit by another active non-bot. Deleted history remains available to trace queries, but does not appear as live file-risk evidence.

## `07_orphaned_decisions.cypher`

**What it answers:** find decisions for which the departing person is the only currently active participant at the requested evidence confidence.

**Parameters:** $login is the person; $minConfidence is 'high' or 'low'.

This filters the departing person?s decision participation by confidence, then checks whether any other active participant meets that same threshold. It returns isolated decisions and possible people to ask.

## `07_orphaned_decisions_graph.cypher`

**What it answers:** show the departing person's participation in each orphaned Decision and every qualifying person to ask.

**Parameters:** $login, $decisions, and $minConfidence select the result evidence.

The query follows confidence-qualified participation from the departing person to each selected Decision, then returns paths from other qualifying participants into those Decisions. These paths support the decision and who-to-ask evidence.

## `07b_decision_share.cypher`

**What it answers:** Report combined decision PR ownership with explicit and title-only counts separately.

**Parameters:** $login, $minShare on combined share, $minConfidence (high or low).

Deduplicate each person/decision/PR before counting; if duplicate links include high confidence, classify that PR as explicit only. Return theirExplicitPRs/explicitPRs and theirTitleMatchPRs/titleMatchPRs alongside combined theirPRs/totalPRs/share. Apply the existing confidence and combined-share filters, aggregate co-openers separately, and sort explicit share first (zero when no explicit PRs), then combined share. For each decision it also returns `prs` (up to five of the person's PRs with confidence and `via`, explicit links first), the tracking `issue` and the RFC document `rfcPath`, which the decision card turns into GitHub links.

## `07b_decision_share_graph.cypher`

**What it answers:** show the PR-opening paths supporting decision-share ownership and the active co-openers to ask.

**Parameters:** $login is the owner being evaluated; $decisions are returned decision titles; $minConfidence is the confidence threshold.

It returns only `Person -OPENED-> PR -IMPLEMENTS-> Decision` paths for selected decisions, filtered to the owner and active other openers.

## `08_successor.cypher`

**What it answers:** Rank Active non-bot successors by shared recent files, then recent component commits.

**Parameters:** $login, $component, $since (epoch ms).

Collect current files touched by the leaving person's in-window non-bulk commits, then aggregate distinct shared files per candidate. Separately count distinct in-window non-bulk commits on all current files in that Component for theirCommits; KNOWS.commits spans all loaded history and cannot supply a recent count.

## `08_successor_graph.cypher`

**What it answers:** show only the shared recent files linking the departing person and ranked successor candidates.

**Parameters:** $login, $successors, $component, and $since identify the overlap result.

The path starts at the departing person, passes through a recent non-bulk commit and extant shared file, then follows the candidate?s non-bulk touching commit. It restricts paths to the selected Component and ranked successors so the evidence matches the overlap that drove the result.

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

Starting at the requested file, this path walks backward through a commit and PR into a decision and its RFC issue. It returns explicit readable properties (file path, commit SHA/time, PR number/title, decision slug/title/status, confidence/source, and issue number) beside the renderable path, preferring stronger links before recency.

## `10b_why_not.cypher`

**What it answers:** explain which accepted decision replaced a rejected decision and who can explain the replacement.

**Parameters:** $slug is the rejected Decision.slug.

This follows SUPERSEDED_BY from the rejected choice to its replacement and issue, and returns the edge's `rationale` (a verbatim excerpt of the replacement's tracking issue) with `rationaleSource`. It also counts later edits to files connected to the replacement; that evidence gates a drift follow-up question.

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

**What it answers:** Compare CODEOWNERS with the top three qualifying recent Module authors.

**Parameters:** $since (epoch ms), $minCommits per author/module.

Collect declarations separately, then count distinct in-window non-bulk commits on current files per non-bot person/module before ranking. KNOWS totals are all-history, so they cannot supply recent rankings. Keep modules with no qualifying authors and exclude below-threshold authors from actualTop3.

## `12_declared_vs_actual_graph.cypher`

**What it answers:** show declared owners and the top three observed experts for each reported Module.

**Parameters:** $areas contains {name, actualTop3}; $modules are the returned Module names.

This returns each Module, its declared owners, and its observed experts as a small evidence subgraph.

## `13_find_entity.cypher`

**What it answers:** resolve free text to people, modules, Components, decisions, or files using graph indexes and string matching.

**Parameters:** $text is the case-insensitive query string; $limit caps results per entity type.

This searches case-folded logins (including partial matches), names, Module and Component names, Decision titles and slugs, and file path suffixes. Exact logins rank first, then login prefixes, then other matches. All candidates are graph nodes with typed keys so later tools can resolve them.

## `13_find_entity_graph.cypher`

**What it answers:** return only the graph entities matched by find_entity, with no neighboring edges.

**Parameters:** $people, $components, $modules, $decisions, and $files are matched keys.

The query matches each result by its label-specific stable key and returns the matching nodes only. It deliberately leaves neighborhood expansion to later graph tools so entity search stays uncluttered.


## Name checks (WP15)

Before an agent tool runs, `tools.resolve_inputs` checks every login, area, decision slug and file path it was given
with the queries below (plus 17c and 17d). If a name is not in the graph, or the person is not Active, nothing else
runs: the tool returns `unknown_entity` or `inactive_person` with suggestions from `13_find_entity`. A known name
whose query returns no rows gets `no_qualifying_evidence`, with the query's threshold, so an empty result never reads
as "nothing at risk".

## `17e_person_status.cypher`

**What it answers:** whether a login belongs to any Person, including inactive people and bots.

**Parameters:** $login is the exact Person.login.

Runs only after `17c_active_person` misses, to tell "in the graph but not Active (or a bot)" from "not in the graph
at all". Returns `active`, `bot` and `lastSeen`, which the agent quotes as the last-seen date.

## `17f_component_prefix.cypher`

**What it answers:** how many Components have names starting with the requested prefix.

**Parameters:** $prefix is a non-empty Component name prefix.

Checks `componentPrefix` in `departure_impact` and `departure_files`; zero means the prefix matches no area.
`count(DISTINCT c)` keeps zero explicit.

## `17g_decision_exists.cypher`

**What it answers:** whether an exact decision slug exists, whatever its status.

**Parameters:** $slug is the exact Decision.slug.

Checks `why_not` and `decision:` correction keys. It separates a missing decision (`unknown_entity`) from one that
exists but was not superseded (`no_qualifying_evidence` from `why_not`).

## `17h_file_exists.cypher`

**What it answers:** whether an exact file path exists in the graph and whether it exists at HEAD.

**Parameters:** $path is the exact File.path.

Checks `decision_trace`. Deleted files stay valid: their history can still be traced.

## `17i_module_exists.cypher`

**What it answers:** whether a correction refers to an existing Module.

**Parameters:** $name is the exact Module.name.

Checks `module:` keys in `remember_correction`.

## `17j_reply_names.cypher`

**What it answers:** which graph names the reply check looks for in the agent's final answer.

**Parameters:** none.

Returns non-bot logins, Component names that contain `/`, and Decision titles with their slugs. After the final
answer, `agent/reply_check.py` finds these names (plus `#1234`-style numbers, `@mentions` and backticked paths) in the
answer and flags any that do not appear in this turn's tool results, the question or the recalled memory. Bots and
single-word areas are left out because they match ordinary words. The answer is never rewritten; unmatched names
appear as a warning under it.
