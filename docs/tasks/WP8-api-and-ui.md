<task>
You are implementing work package WP8 of "Bus Factor" (Graph Hacks, FalkorDB). Read AGENTS.md, docs/PLAN.md,
docs/PROGRESS.md, docs/QUERIES.md and README.md. The graph, tools (src/busfactor/tools.py) and the agent
(src/busfactor/agent/, WP7) exist. Hard rule: the UI must show the graph path behind each answer.

Scope: a small HTTP API and a single-page UI. No frontend build step; no framework that hides the Cypher.

Build:
1. API (FastAPI 0.143.3 and uvicorn 0.54.0 are already installed by the reviewer; for TestClient you may also need
   httpx, which is installed):
   src/busfactor/api/app.py
   - GET  /api/health -> FalkorDB reachable, graph node/edge counts, agent model name.
   - POST /api/ask {question, user, sessionId?} -> the agent's AgentAnswer (answer, tool_calls with cypher, graph,
     entities, stop_reason, usage, memory recall used).
   - GET  /api/tools -> list of tools with parameter schemas; POST /api/tools/{name} {params} -> the tool result
     (rows, cypher, graph). Lets the UI run a tool directly without the LLM.
   - GET  /api/departure/{login} -> one call that runs simulate_departure, departure_impact, departure_files,
     decision_share and successor for the top orphaned component, and returns them together (the headline panel;
     no LLM needed).
   - GET  /api/memory/{user} -> what the user's memory graph holds.
   - Serve web/ as static files at /. Bind to 127.0.0.1 by default (env HOST/PORT).
   `python -m busfactor.api` starts it.
2. UI: web/index.html + web/app.js + web/style.css, plain JS, Cytoscape.js from cdnjs pinned to an exact version.
   Layout: left = chat (question box, answers, and under each answer a collapsible "How I know" list of tool calls
   with their Cypher in a <pre>); right = graph canvas showing the evidence graph of the selected answer (node
   colours by label: Person, Component, Module, File, Commit, PR, Decision, Issue; edge labels by type; click a node
   to see its properties). A "Departure simulator" tab: pick a person (find_entity search), see the headline panel
   (main group before/after, cut-off people, ORPHANED / AT RISK components, orphaned files by component, decisions
   they carry and who to ask, best successor) with its graph. Show the memory recall ("Last time you asked ...;
   since then N new commits in X") at the top of a new session.
   Keep it readable at 1280px and usable at 390px wide. No external fonts. Light theme is enough.
3. Tests: FastAPI TestClient tests for /api/health, /api/tools, /api/tools/{name} and /api/departure/{login} on the
   fixture graph (monkeypatch the graph name), and /api/ask with AGENT_PROVIDER=scripted.
4. README: "Run the app" section (docker compose up -d; load pipeline; python -m busfactor.api; open
   http://127.0.0.1:8000). Append to docs/PROGRESS.md.
</task>

<action_safety>
Stay inside this scope. Do not touch AGENTS.md, CLAUDE.md, docs/PLAN.md, docs/tasks/, or data/delta. Do not run git
commit. Never send API keys to the browser; the browser talks only to our API.
</action_safety>

<verification_loop>
pytest must pass. Start the server and fetch /api/health and /api/departure/murali-db with curl; include the JSON
(trimmed). Do not make live LLM calls; the reviewer tests /api/ask live.
</verification_loop>

<compact_output_contract>
Files changed; pytest summary; the curl outputs; decisions for the reviewer; anything uncertain.
</compact_output_contract>
