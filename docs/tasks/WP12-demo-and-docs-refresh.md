<task>
You are updating the submission docs of "Bus Factor" after the UX revamp (WP11a-d). Read AGENTS.md, README.md,
docs/DEMO.md, docs/BLOG.md, docs/tasks/WP11-ux-revamp-plan.md and the current UI source (web/index.html, web/app.js)
so every label, button and flow you describe matches the real UI. Use `.venv/Scripts/python` for live numbers; FalkorDB
is at 127.0.0.1 with the live `delta` graph. Edit only docs/DEMO.md, README.md and docs/BLOG.md (and docs/PROGRESS.md:
one line). No code changes.

docs/DEMO.md is stale: it mentions a "Departure simulator" tab, a "Find" button, "leave the user login as murali-db",
a "Team memory" panel in Ask, "Run a graph tool directly", and the mem_murali-db graph. None of these exist now.

1. Rewrite docs/DEMO.md as a 3-minute script for the current UI, with exact clicks and the labels as they appear:
   - Opening on the "What if someone leaves?" tab: the headline number as the page heading (read it from
     /api/summary), "What is a bus factor?", the maintainer search (click it: the top 10 by recent commits; type "m";
     pick Murali Ramanujam with ↓ and Enter), the one-sentence summary, the sections with counts, "Show successors" on
     one area, the departure graph beside the results (person in the centre), "Ask about this".
   - Second person: scottsand-db (decision share: Catalog-Managed Tables 43 of 88 PRs).
   - "Ask" tab: a starter question chip (goes to the agent when the server has a key), Tab completion (type "Why was",
     press Tab), Enter to send, the answer in view, "How I know" with the tool labels and Cypher, the follow-up chips.
   - Memory (Track 02): reload the page in the same browser to show "Welcome back. Last time you asked …"; open an
     incognito window to show a new anonymous visitor with no history; mention "Start over". Explain the
     mem_v_<id> per-visitor graph and the shared mem_team graph in one sentence each.
   - Refresh and team memory (local dev only): `.venv/Scripts/python -m busfactor.refresh` and the "Recent changes in
     the repo" line on the landing page.
   - A "Before recording" checklist (server with key, a fresh browser profile so earlier test history does not show,
     window size about 1280 x 765 or larger) and a "No API key" variant (starter chips show readable tables).
   - Expected values "as of 2026-10-17" from the live graph for murali-db and scottsand-db (summary sentence numbers,
     decision share, top successor) and the headline numbers; keep them in one small table.
   - A one-line note on timing from the server log (graph tools about 0.3 s; the model takes most of a 10-20 s answer).
2. README.md: check every UI description against the current UI and fix stale ones (tab names, no login, starter
   questions, Tab completion, follow-ups, evidence panel beside results, chat-disabled behaviour). Add a short
   "What you can do" list near the top (3-4 bullets) for a newcomer. Do not touch the AI-assistance section except to add
   that the UX revamp plan was reviewed by Codex on GPT-6-Astra before implementation and is in docs/tasks/WP11-*.
3. docs/BLOG.md: add one short paragraph on designing for a newcomer (no sign-in, the number first, a ranked
   maintainer search, follow-up questions built from graph rows rather than model prose, the layout bug found by the
   developer's own test), keeping the post under 1,200 words and its honest tone.
</task>

<action_safety>
Docs only. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md or docs/tasks/. Do not run git commit. No live LLM calls.
Never mention employers or internal projects.
</action_safety>

<verification_loop>
Check each UI label you cite exists in web/index.html or web/app.js (grep) and list any you could not find.
</verification_loop>

<compact_output_contract>
Files changed; the values table you put in DEMO.md; any label you could not verify.
</compact_output_contract>
