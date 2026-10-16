<task>
You are implementing work package WP4 of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md,
docs/PLAN.md (Decision, IMPLEMENTS, the notes under the relationship table) and docs/PROGRESS.md.
WP1-WP3 are done; follow their conventions (db.run_query(bare name), header comments, PLAN numbering
with letter suffixes, Person.login lower-cased, bots excluded from derived edges).

Goal: PR -[:IMPLEMENTS {via, confidence}]-> Decision, so "why does this code work this way?" can walk
File <- Commit -> PR -> Decision -> Issue. Three sources, strongest first:
1. via 'issue-ref', confidence 'high': the PR body cites the RFC's tracking issue. This is pure graph:
   (pr:PR)-[:REFERENCES]->(:Issue)<-[:TRACKED_IN]-(d:Decision). Write it as a Cypher derive query.
2. via 'rfc-doc', confidence 'high': the PR changed the RFC document itself. Also pure graph:
   (d:Decision) with RFC file stem = d.slug; any File whose path starts with 'protocol_rfcs/' and ends with
   '/' + d.slug + '.md' (accepted RFCs moved from protocol_rfcs/x.md to protocol_rfcs/accepted/x.md, and we
   parse git with --no-renames, so both paths exist as File nodes) <-[:TOUCHED]- Commit -[:PART_OF]-> PR.
   Do not count template.md or README.md.
3. via 'title-keyword', confidence 'low': the PR title (for squash merges this equals the commit subject
   without the `(#N)`) mentions the feature. Do this in Python with a curated keyword table, then load rows.

Build:
1. src/busfactor/decision_keywords.py: KEYWORDS = {slug: [regex, ...]} for all 19 slugs (read slugs from
   data/raw/rfcs.json; fail if a slug has no entry, empty list allowed but explicit). Rules:
   - word boundaries on every pattern; ICT must be case-sensitive uppercase `\bICT\b` (a loose match hits
     "conflict" and "dict"); everything else case-insensitive;
   - avoid generic words that would flood links: no bare "variant" for variant-shredding, no "file type",
     no bare "interval" unless next to "type", no bare "timestamp";
   - Managed Commits was renamed Coordinated Commits before it was rejected; "coordinated commits" maps to
     managed-commits;
   - prefer feature-flag spellings too (e.g. `catalogManaged`, `typeWidening`, `IcebergCompatV3`).
   Calibration data from commit subjects since 2024-10-15 (case-insensitive unless noted):
   catalog[- ]managed 17, coordinated commits 6, \bICT\b (case-sensitive) 11, type widening 30, shredd 17,
   collat 13, IcebergWriterCompatV1 13, IcebergCompatV3 11, identity column 12, materializ.*partition 9,
   checkpoint protection 1, nanosecond 1, UDT/user-defined type 1, in-commit timestamp 0, vacuum protocol 0.
   Use `git -C data/delta log` yourself to check precision: print every subject each pattern matches and
   remove patterns that produce obvious false positives. Put a short comment above each slug's patterns
   saying why.
2. src/busfactor/link_decisions.py: `python -m busfactor.link_decisions` runs, in order:
   queries/04d_derive_implements_issue_ref.cypher, queries/04e_derive_implements_rfc_doc.cypher, then the
   keyword rows into queries/04f_load_implements_keyword.cypher (UNWIND $rows {pr, slug, pattern}).
   An IMPLEMENTS edge keeps the strongest evidence: never downgrade an existing 'high' edge to 'low'
   (MERGE the edge, then SET confidence/via only when the new one is stronger or the edge is new; keep a
   `sources` list of all vias that found it). Before writing, delete IMPLEMENTS edges whose only source is
   'title-keyword' so re-runs reflect the current keyword table.
   Titles come from PR nodes (pr.title) when present; if PR nodes are missing, fall back to commit subjects
   from data/raw/git_log.json so the matcher can be tested before the API data exists.
   Print: edges per via, edges per decision (table), and for each decision the 3 most recent linked PRs.
3. Because PARTICIPATED_IN (WP3, 04b) derives from IMPLEMENTS, link_decisions must run before
   derive's 04b/04c. Document the full order in README "Pipeline" (load all -> link_decisions -> derive).
   Decide whether 'low' links should create PARTICIPATED_IN; recommend and implement one choice, and
   explain it in the 04b header (hint: a low-confidence title match plus authorship is still evidence of
   participation, but the agent must be able to filter by confidence; consider copying confidence onto
   PARTICIPATED_IN).
4. tests/: keyword precision tests (positive and negative examples per tricky slug: ICT vs "conflict",
   "dict", "ICTs"; variant-shredding vs "variant type"; managed-commits vs "coordinated commits"), the
   strongest-evidence rule (pure Python helper), and that every query file has a header and its params.
5. Append one line to docs/PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta (read-only
git commands are fine). Do not run git commit. No LLM calls; this is deterministic.
</action_safety>

<verification_loop>
`.venv/Scripts/python -m pytest -q` must pass. Run the keyword matcher against commit subjects (the
fallback path) and include per-decision match counts. If FalkorDB is reachable, run link_decisions and
include its output; otherwise say so.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; per-decision keyword match counts on commit subjects; patterns you removed
for false positives (with an example); decisions for the reviewer; anything uncertain.
</compact_output_contract>
