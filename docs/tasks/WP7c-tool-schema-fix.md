<task>
You are implementing a small fix package, WP7c, for "Bus Factor". Read AGENTS.md and docs/PROGRESS.md. All earlier
packages are committed.

Live regression found by the reviewer: every /api/ask now fails with
  400 invalid_request_error: "Schemas contains too many optional parameters (26), which would make grammar
  compilation inefficient. Reduce the number of optional parameters in your tool schemas (limit: 24)."
WP7b added optional parameters (includeTestResources, componentPrefix) to tools that are sent to Claude with
strict: true. The limit counts optional parameters across all tools in one request.

Fixes:
1. Separate the LLM-facing tool schema from the full Python signature. The model sees only parameters that change the
   meaning of the question: login, component, componentPrefix, path, text, slug, minConfidence (and limit only where it
   matters, e.g. bridges). Tuning parameters (since, minCommits, minTotal, minShare, maxFileCommits,
   includeTestResources, limit elsewhere) keep their server-side defaults and stay available to the UI/CLI through
   tools.py. Put the LLM-facing parameter list per tool in one explicit table in tools.py (or agent/llm.py) so it is
   easy to explain.
2. Add a unit test that builds the exact tool list sent to Claude and asserts the total number of optional parameters
   is <= 20 (headroom under the API limit of 24), every schema has additionalProperties false, and every required
   parameter exists in the Python function.
3. Add scripts/smoke_live.py: an opt-in live check (skips with a clear message when ANTHROPIC_API_KEY is not set) that
   sends one short question through ask() and prints stop_reason, tool names and seconds. Not part of pytest.
4. UI (small): draw the departure focus graph with a layout centred on the departing person (concentric by distance
   from the person, or breadthfirst rooted at the person) instead of cose; keep cose for the full-evidence view.
   Add cache-busting for static files (e.g. app.js?v=<git short sha or file mtime> in index.html served by the API, or
   Cache-Control: no-cache on / and static files) so a reload never shows a stale app.js.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/ or data/delta. Do not run git
commit. Do not make live LLM calls (the reviewer runs smoke_live.py).
</action_safety>

<verification_loop>
pytest must pass. Print the optional-parameter count per tool and the total.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary; the optional-parameter table.
</compact_output_contract>
